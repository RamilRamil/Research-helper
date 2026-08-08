---
type: Reference
title: Configuration — env, Docker Compose, local dev
description: Environment variables, the db/app Compose services, dependencies, and the manual schema-init caveat.
tags: [configuration, docker, env, deployment]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: docker-compose.yml
    title: db + app services
  - resource: .env.example
    title: environment variables
  - resource: Dockerfile
    title: app image
  - resource: requirements.txt
    title: dependencies
---

# Configuration

🇷🇺 [Русская версия](configuration.ru.md)

How the bot is configured and run. Loaded from `.env` via `python-dotenv`.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `TELEGRAM_TOKEN` | yes | Bot token; `bot/main.py` reads it at import. |
| `ALLOWED_USER_ID` | yes | Integer Telegram user id — the single whitelisted user. |
| `GEMINI_API_KEY` | yes | Used for both embeddings and generation. |
| `DATABASE_URL` | yes | Postgres DSN. Local default targets `localhost:5433`; Compose overrides it to the internal `db:5432`. |
| `PAPERS_DIR` | no | PDF storage dir; defaults to `data/papers`. |
| `GROQ_API_KEY` | no | Present in `.env.example` but **not used** — no Groq is wired (see [system-overview.md](system-overview.md)). |

Never commit `.env` — it is gitignored.

## Docker Compose

[docker-compose.yml](../docker-compose.yml) defines two services:

- **`db`** — `pgvector/pgvector:pg16`, database/user/password all `research`, published on host
  port **5433** → container 5432, with a `pg_isready` healthcheck and a `pgdata` named volume.
- **`app`** — built from the [Dockerfile](../Dockerfile), `env_file: .env`, with `DATABASE_URL`
  overridden to `postgresql://research:research@db:5432/research`. Starts only after `db` is
  healthy, `restart: unless-stopped`, and mounts `./data/papers` so PDFs persist on the host.

## Local development

```bash
cp .env.example .env          # fill TELEGRAM_TOKEN, ALLOWED_USER_ID, GEMINI_API_KEY
docker compose up -d db       # Postgres on localhost:5433
python -m app.bot.main        # run the bot against the local DB
```

Dependencies ([requirements.txt](../requirements.txt)): `python-dotenv`, `psycopg[binary]`,
`aiogram`, `arxiv`, `pymupdf`, `httpx`, `google-genai`. Python 3.12.

## ⚠ Schema init is manual

The [Dockerfile](../Dockerfile) copies only `app/` — **`scripts/` is not in the image**, so the
Compose stack does **not** auto-apply `init_db.sql` or the migrations. The schema must be created
by hand against the database (e.g. `psql "$DATABASE_URL" -f scripts/init_db.sql`, then the chunks +
FTS + halfvec/HNSW migrations). See [database.md](database.md) for the file order and the caveat
about `add_chunks.sql`.
