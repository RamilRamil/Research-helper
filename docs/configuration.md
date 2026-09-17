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
| `ALLOWED_USERS` | yes* | Multi-user allowlist: `telegram_id:role` comma-separated. Roles: `admin`, `reader`. Preferred. |
| `ALLOWED_USER_ID` | legacy* | Single Telegram user id treated as one `admin` when `ALLOWED_USERS` is unset/empty. |

\* Bot fails closed unless `ALLOWED_USERS` or legacy `ALLOWED_USER_ID` is set.
| `GEMINI_API_KEY` | yes | Used for query and document embeddings. |
| `OPENROUTER_API_KEY` | yes | Used for DeepSeek V3.2 generation. |
| `MCP_HTTP_HOST` | no | Default `0.0.0.0`. |
| `MCP_HTTP_PORT` | no | Default `8000`. |
| `MCP_RATE_LIMIT_PER_MIN` | no | Default `60` requests per minute (per IP before auth, per credential after). |
| `MCP_RESOURCE_URL` | no | Public MCP resource URL for auth metadata. |
| `DATABASE_URL` | yes | Postgres DSN. Local default targets `localhost:5433`; Compose overrides it to the internal `db:5432`. |
| `PAPERS_DIR` | no | PDF storage dir; defaults to `data/papers`. |
| `GROQ_API_KEY` | no | Present in `.env.example` but **not used** — no Groq is wired (see [system-overview.md](system-overview.md)). |

Never commit `.env` — it is gitignored.

## Docker Compose

[docker-compose.yml](../docker-compose.yml) defines services:

- **`db`** — `pgvector/pgvector:pg16`, database/user/password all `research`, published on host
  port **5433** → container 5432, with a `pg_isready` healthcheck and a `pgdata` named volume.
- **`app`** — built from the [Dockerfile](../Dockerfile), `env_file: .env`, with `DATABASE_URL`
  overridden to `postgresql://research:research@db:5432/research`. Starts only after `db` is
  healthy, `restart: unless-stopped`, and mounts `./data/papers` so PDFs persist on the host.
- **`mcp`** — Streamable HTTP MCP (`python -m app.mcp_server --http`) on port 8000.
- **`mcp_worker`** — drains `mcp_topic_jobs` (search + ingest); no published ports.

## Local development

```bash
cp .env.example .env          # fill TELEGRAM_TOKEN, ALLOWED_USERS (or ALLOWED_USER_ID), GEMINI_API_KEY
docker compose up -d db       # Postgres on localhost:5433
python -m app.bot.main        # run the bot against the local DB
```

Dependencies ([requirements.txt](../requirements.txt)): `python-dotenv`, `psycopg[binary]`,
`aiogram`, `arxiv`, `pymupdf`, `httpx`, `google-genai`, and `mcp`. Python 3.12.

## Local MCP server

Agent playbook (same machine + Docker): [mcp-agent-connect.md](mcp-agent-connect.md).

The read-only MCP server exposes `list_papers`, `get_paper`, `get_paper_chunks`,
and `search`. Admin HTTP also exposes `request_topic_ingest` and
`get_topic_ingest_job`.

### Stdio

```bash
docker compose run --rm -T app python -m app.mcp_server
```

### Streamable HTTP (DB credentials + rate limit)

Apply schema and mint a credential first:

```bash
psql "$DATABASE_URL" -f scripts/mcp_tokens.sql
python -m app.mcp_tokens create --label alice --role reader
```

Then:

```bash
docker compose up -d --build mcp
```

Endpoint: `http://127.0.0.1:8000/mcp`  
Auth: `Authorization: Bearer <token_from_mint>` (per-client DB credential; former
`MCP_TOKEN` env secret is not used)  
Rate limit: `MCP_RATE_LIMIT_PER_MIN` (default 60/min; IP key before identity,
credential key after verify).

Revoke:

```bash
python -m app.mcp_tokens revoke --label alice
```

`get_paper_chunks` pages live indexed body text (`limit` default 20, max 50;
`offset` from 0). Repeat until `offset + returned >= total`.

### Topic ingest (admin HTTP)

Compose worker drains durable jobs:

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_topic_jobs.sql
docker compose run --rm -T app python -m app.mcp_tokens create --label agent-admin --role admin
docker compose up -d --build mcp mcp_worker
```

MCP tools (Bearer **admin** only for enqueue):

- `request_topic_ingest(topic)` → `{job_id, status, topic}`
- `get_topic_ingest_job(job_id)` → status + counts (creator-only)

Poll until `status` is `succeeded` or `failed`. Stdio cannot enqueue (no
credential identity).

Put TLS in front of this service for public internet. The app itself serves
cleartext HTTP.

## ⚠ Schema init is manual

The [Dockerfile](../Dockerfile) copies only `app/` — **`scripts/` is not in the image**, so the
Compose stack does **not** auto-apply `init_db.sql` or the migrations. The schema must be created
by hand against the database (e.g. `psql "$DATABASE_URL" -f scripts/init_db.sql`, then the chunks +
FTS + halfvec/HNSW migrations). See [database.md](database.md) for the file order and the caveat
about `add_chunks.sql`.
