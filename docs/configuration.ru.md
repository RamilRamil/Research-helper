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
| `ALLOWED_USER_ID` | да | Целочисленный Telegram user id — единственный whitelisted пользователь. |
| `GEMINI_API_KEY` | да | Используется для query/document эмбеддингов. |
| `OPENROUTER_API_KEY` | да | Используется для генерации DeepSeek V3.2. |
| `MCP_TOKEN` | да для HTTP MCP | Shared bearer token для Streamable HTTP. |
| `MCP_HTTP_HOST` | нет | По умолчанию `0.0.0.0`. |
| `MCP_HTTP_PORT` | нет | По умолчанию `8000`. |
| `MCP_RATE_LIMIT_PER_MIN` | нет | По умолчанию `60` запросов на IP в минуту. |
| `MCP_RESOURCE_URL` | нет | Публичный URL MCP resource для auth metadata. |
| `DATABASE_URL` | да | Postgres DSN. Локальный дефолт — `localhost:5433`; Compose переопределяет на внутренний `db:5432`. |
| `PAPERS_DIR` | нет | Каталог хранения PDF; по умолчанию `data/papers`. |
| `GROQ_API_KEY` | нет | Есть в `.env.example`, но **не используется** — Groq не подключён (см. [system-overview.ru.md](system-overview.ru.md)). |

Никогда не коммить `.env` — он в gitignore.

## Docker Compose

[docker-compose.yml](../docker-compose.yml) определяет два сервиса:

- **`db`** — `pgvector/pgvector:pg16`, база/пользователь/пароль все `research`, опубликован на
  хост-порту **5433** → контейнерный 5432, с healthcheck `pg_isready` и именованным томом
  `pgdata`.
- **`app`** — собирается из [Dockerfile](../Dockerfile), `env_file: .env`, с `DATABASE_URL`
  переопределённым на `postgresql://research:research@db:5432/research`. Стартует только после того,
  как `db` healthy, `restart: unless-stopped`, монтирует `./data/papers`, чтобы PDF сохранялись на
  хосте.

## Локальная разработка

```bash
cp .env.example .env          # заполнить TELEGRAM_TOKEN, ALLOWED_USER_ID, GEMINI_API_KEY
docker compose up -d db       # Postgres на localhost:5433
python -m app.bot.main        # запустить бота против локальной БД
```

Зависимости ([requirements.txt](../requirements.txt)): `python-dotenv`, `psycopg[binary]`,
`aiogram`, `arxiv`, `pymupdf`, `httpx`, `google-genai` и `mcp`. Python 3.12.

## Локальный MCP server

Read-only MCP server отдаёт `list_papers`, `get_paper` и `search`.
Write-tools нет.

### Stdio

```bash
docker compose run --rm -T app python -m app.mcp_server
```

### Streamable HTTP (token + rate limit)

Задай `MCP_TOKEN` в `.env`, затем:

```bash
docker compose up -d --build mcp
```

Endpoint: `http://127.0.0.1:8000/mcp`  
Auth: `Authorization: Bearer <MCP_TOKEN>`  
Rate limit: `MCP_RATE_LIMIT_PER_MIN` (по умолчанию 60/мин на IP).

Для публичного интернета поставь TLS перед сервисом. Само приложение
отдаёт cleartext HTTP.

## ⚠ Инициализация схемы ручная

[Dockerfile](../Dockerfile) копирует только `app/` — **`scripts/` не попадает в образ**, поэтому
Compose-стек **не** применяет автоматически `init_db.sql` и миграции. Схему нужно создавать вручную
против базы (например `psql "$DATABASE_URL" -f scripts/init_db.sql`, затем миграции chunks + FTS +
halfvec/HNSW). Порядок файлов и оговорку про `add_chunks.sql` см. в [database.ru.md](database.ru.md).
