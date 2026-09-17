---
type: Reference
title: Конфигурация — env, Docker Compose, локальная разработка
description: Переменные окружения, Compose-сервисы db/app, зависимости и оговорка про ручную инициализацию схемы.
tags: [configuration, docker, env, deployment]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: docker-compose.yml
    title: сервисы db + app
  - resource: .env.example
    title: переменные окружения
  - resource: Dockerfile
    title: образ app
  - resource: requirements.txt
    title: зависимости
---

# Конфигурация

🇬🇧 [English version](configuration.md)

Как бот конфигурируется и запускается. Загружается из `.env` через `python-dotenv`.

## Переменные окружения

| Переменная | Обязательна | Заметки |
|---|---|---|
| `TELEGRAM_TOKEN` | да | Токен бота; `bot/main.py` читает его при импорте. |
| `ALLOWED_USERS` | да* | Multi-user allowlist: `telegram_id:role` через запятую. Роли: `admin`, `reader`. Предпочтительный вариант. |
| `ALLOWED_USER_ID` | legacy* | Один Telegram user id как единственный `admin`, если `ALLOWED_USERS` не задан/пуст. |

\* Бот fail closed, пока не задан `ALLOWED_USERS` или legacy `ALLOWED_USER_ID`.
| `GEMINI_API_KEY` | да | Используется для query/document эмбеддингов. |
| `OPENROUTER_API_KEY` | да | Используется для генерации DeepSeek V3.2. |
| `MCP_HTTP_HOST` | нет | По умолчанию `0.0.0.0`. |
| `MCP_HTTP_PORT` | нет | По умолчанию `8000`. |
| `MCP_RATE_LIMIT_PER_MIN` | нет | По умолчанию `60` запросов в минуту (по IP до auth, по credential после). |
| `MCP_RESOURCE_URL` | нет | Публичный URL MCP resource для auth metadata. |
| `DATABASE_URL` | да | Postgres DSN. Локальный дефолт — `localhost:5433`; Compose переопределяет на внутренний `db:5432`. |
| `PAPERS_DIR` | нет | Каталог хранения PDF; по умолчанию `data/papers`. |
| `GROQ_API_KEY` | нет | Есть в `.env.example`, но **не используется** — Groq не подключён (см. [system-overview.ru.md](system-overview.ru.md)). |

Никогда не коммить `.env` — он в gitignore.

## Docker Compose

[docker-compose.yml](../docker-compose.yml) определяет сервисы:

- **`db`** — `pgvector/pgvector:pg16`, база/пользователь/пароль все `research`, опубликован на
  хост-порту **5433** → контейнерный 5432, с healthcheck `pg_isready` и именованным томом
  `pgdata`.
- **`app`** — собирается из [Dockerfile](../Dockerfile), `env_file: .env`, с `DATABASE_URL`
  переопределённым на `postgresql://research:research@db:5432/research`. Стартует только после того,
  как `db` healthy, `restart: unless-stopped`, монтирует `./data/papers`, чтобы PDF сохранялись на
  хосте.
- **`mcp`** — Streamable HTTP MCP на порту 8000.
- **`mcp_worker`** — drain `mcp_topic_jobs` (search + ingest); без published ports.

## Локальная разработка

```bash
cp .env.example .env          # заполнить TELEGRAM_TOKEN, ALLOWED_USERS (или ALLOWED_USER_ID), GEMINI_API_KEY
docker compose up -d db       # Postgres на localhost:5433
python -m app.bot.main        # запустить бота против локальной БД
```

Зависимости ([requirements.txt](../requirements.txt)): `python-dotenv`, `psycopg[binary]`,
`aiogram`, `arxiv`, `pymupdf`, `httpx`, `google-genai` и `mcp`. Python 3.12.

## Локальный MCP server

Playbook для агента на этой машине (Docker): [mcp-agent-connect.ru.md](mcp-agent-connect.ru.md).

Read-only MCP tools: `list_papers`, `get_paper`, `get_paper_chunks`, `search`.
Admin HTTP additionally: `request_topic_ingest`, `get_topic_ingest_job`.

### Stdio

```bash
docker compose run --rm -T app python -m app.mcp_server
```

### Streamable HTTP (DB credentials + rate limit)

Сначала схема и mint:

```bash
psql "$DATABASE_URL" -f scripts/mcp_tokens.sql
python -m app.mcp_tokens create --label alice --role reader
```

Затем:

```bash
docker compose up -d --build mcp
```

Endpoint: `http://127.0.0.1:8000/mcp`  
Auth: `Authorization: Bearer <token_from_mint>` (per-client DB credential; бывший
`MCP_TOKEN` из env не используется)  
Rate limit: `MCP_RATE_LIMIT_PER_MIN` (по умолчанию 60/мин; ключ IP до identity,
ключ credential после verify).

Revoke:

```bash
python -m app.mcp_tokens revoke --label alice
```

`get_paper_chunks` листает live indexed body (`limit` по умолчанию 20, max 50;
`offset` с 0). Повторять, пока `offset + returned >= total`.

### Topic ingest (admin HTTP)

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_topic_jobs.sql
docker compose run --rm -T app python -m app.mcp_tokens create --label agent-admin --role admin
docker compose up -d --build mcp mcp_worker
```

Tools (Bearer **admin** для enqueue):

- `request_topic_ingest(topic)` → `{job_id, status, topic}`
- `get_topic_ingest_job(job_id)` → статус + counts (только creator)

Poll до `succeeded` / `failed`. Stdio enqueue не умеет.

Для публичного интернета поставь TLS перед сервисом. Само приложение
отдаёт cleartext HTTP.

## ⚠ Инициализация схемы ручная

[Dockerfile](../Dockerfile) копирует только `app/` — **`scripts/` не попадает в образ**, поэтому
Compose-стек **не** применяет автоматически `init_db.sql` и миграции. Схему нужно создавать вручную
против базы (например `psql "$DATABASE_URL" -f scripts/init_db.sql`, затем миграции chunks + FTS +
halfvec/HNSW). Порядок файлов и оговорку про `add_chunks.sql` см. в [database.ru.md](database.ru.md).
