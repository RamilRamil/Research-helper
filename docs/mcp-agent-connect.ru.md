---
type: Reference
title: Подключение MCP — playbook для агента на этой машине
description: Пошаговая инструкция агенту на этом хосте подключить research-library MCP через Docker.
tags: [mcp, docker, agent, operator]
lang: ru
status: draft
---

# Подключение MCP — playbook для агента на этой машине

🇬🇧 [English version](mcp-agent-connect.md)

**Кому:** агент на **той же машине**, что и репозиторий, с доступом к Docker
как у обычного dev-шелла.

**Цель:** подключить read-only MCP `research-library` и вызывать tools.

Не поднимай второй сервер. Не используй устаревший `MCP_TOKEN` из env.

## 0. Корень репо

Команды из каталога, где есть `docker-compose.yml` и `app/mcp_server.py`.

```bash
test -f docker-compose.yml && test -f app/mcp_server.py
```

## 1. Postgres

```bash
docker compose up -d db
docker compose ps
```

Дождись healthy у `db`.

## 2. Таблица credentials

`scripts/` не в образе app. Накати SQL так:

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_tokens.sql
```

Повторный запуск безопасен.

## 3. Транспорт

| Режим | Когда | Auth |
|------|------|------|
| **HTTP (предпочтительно здесь)** | Долгий агент / URL в Cursor | Bearer после mint |
| **stdio** | Клиент сам спавнит процесс | Без Bearer (host trust) |

### 3a. HTTP

```bash
docker compose run --rm -T app python -m app.mcp_tokens create --label local-agent --role reader
# для request_topic_ingest нужен admin:
docker compose run --rm -T app python -m app.mcp_tokens create --label local-admin --role admin
```

Сохрани `token=...`. Если label занят: `revoke` затем `create`.

```bash
docker compose up -d --build mcp mcp_worker
```

URL: `http://127.0.0.1:8000/mcp`  
Header: `Authorization: Bearer <token>`

Пример конфига клиента:

```json
{
  "mcpServers": {
    "research-library": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer REPLACE_WITH_MINTED_TOKEN"
      }
    }
  }
}
```

### 3b. stdio

```json
{
  "mcpServers": {
    "research-library": {
      "command": "docker",
      "args": [
        "compose",
        "run",
        "--rm",
        "-T",
        "app",
        "python",
        "-m",
        "app.mcp_server"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/THIS/REPO"
    }
  }
}
```

Stdout = протокол MCP. Не перехватывай stdout логгером.

## 4. Smoke

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/mcp
```

В клиенте: list tools → `list_papers` с `limit=3`.

## 5. Tools

| Tool | Зачем |
|------|--------|
| `list_papers` | Страница метаданных indexed |
| `get_paper` | Мета + summaries (не полный текст) |
| `get_paper_chunks` | Полный body по страницам |
| `search` | Hybrid search |
| `request_topic_ingest` | **Admin HTTP** — async search+ingest → `job_id` |
| `get_topic_ingest_job` | **HTTP** — poll статуса (только creator) |

Полная статья: крутить `get_paper_chunks`, пока `offset + returned < total`.

Тема не в библиотеке (admin):

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_topic_jobs.sql
docker compose run --rm -T app python -m app.mcp_tokens create --label local-admin --role admin
docker compose up -d --build mcp mcp_worker
```

MCP: `request_topic_ingest` → poll `get_topic_ingest_job`.

## 6. Типовые сбои

| Симптом | Что делать |
|---------|------------|
| HTTP всегда reject | Нет active credentials — mint; `MCP_TOKEN` env не работает |
| duplicate label | `revoke` + `create` |
| stdio без DB | `docker compose up -d db` |
| нет `get_paper_chunks` | `docker compose up -d --build mcp` |
| 429 | Подождать ~60с |

## См. также

- [configuration.ru.md](configuration.ru.md)
- [`../specs/020-mcp-user-tokens/quickstart.md`](../specs/020-mcp-user-tokens/quickstart.md)
- [`../specs/024-mcp-paper-chunks/spec.md`](../specs/024-mcp-paper-chunks/spec.md)
