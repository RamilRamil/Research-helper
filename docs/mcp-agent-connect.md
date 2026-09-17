---
type: Reference
title: MCP connect — same-machine agent playbook
description: Step-by-step instructions for an agent on this host to attach to the research-library MCP (Docker).
tags: [mcp, docker, agent, operator]
lang: en
status: draft
---

# MCP connect — same-machine agent playbook

🇷🇺 [Русская версия](mcp-agent-connect.ru.md)

**Audience:** an automated agent on the **same machine** as this repo, with Docker
access equivalent to a normal developer shell (compose against this project).

**Goal:** attach to the read-only research-library MCP and call tools.

Do not invent a second server. Do not use the retired env var `MCP_TOKEN`.

## 0. Locate the repo

Work from the git root that contains `docker-compose.yml` and `app/mcp_server.py`.
All commands below assume that directory is the shell cwd.

```bash
test -f docker-compose.yml && test -f app/mcp_server.py
```

## 1. Bring up Postgres

```bash
docker compose up -d db
docker compose ps
```

Wait until `db` is healthy.

## 2. Ensure MCP credential table exists

`scripts/` is not copied into the app image. Apply SQL from the host against
published port **5433**:

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_tokens.sql
```

Safe to re-run (`IF NOT EXISTS`).

## 3. Choose transport

| Mode | When | Auth |
|------|------|------|
| **HTTP (preferred on this host)** | Long-lived agent / Cursor remote MCP URL | Bearer from mint |
| **stdio** | Client spawns the server as a subprocess | None (host trust) |

### 3a. HTTP — mint token + start `mcp` service

Mint (secret printed **once**). Use `reader` for read-only; use `admin` to
enqueue topic ingest:

```bash
docker compose run --rm -T app python -m app.mcp_tokens create --label local-agent --role reader
# or:
docker compose run --rm -T app python -m app.mcp_tokens create --label local-admin --role admin
```

Copy the `token=...` line. If label `local-agent` already exists and is active:

```bash
docker compose run --rm -T app python -m app.mcp_tokens revoke --label local-agent
docker compose run --rm -T app python -m app.mcp_tokens create --label local-agent --role reader
```

Start HTTP MCP + optional ingest worker (rebuild if `app/` changed):

```bash
docker compose up -d --build mcp mcp_worker
```

Endpoint: `http://127.0.0.1:8000/mcp`  
Header: `Authorization: Bearer <token>`

Cursor / MCP host config shape (fill token; path not required):

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

Exact key names vary by host (`mcpServers` vs `mcp`). Keep URL + Bearer.

### 3b. stdio — client spawns Docker

No Bearer. DB must be up. Example Cursor-style config (set `cwd` to this repo
absolute path):

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

Stdout is the MCP protocol stream. Do not wrap the command in loggers that
steal stdout.

## 4. Smoke test

After HTTP is up:

```bash
# expect non-404 / auth challenge without token; with token, MCP session works
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/mcp
```

Then from the MCP client: list tools, call `list_papers` with `limit=3`.

## 5. Tools (read-only + admin jobs)

| Tool | Purpose |
|------|---------|
| `list_papers` | Indexed metadata page (`limit`/`offset`) |
| `get_paper` | One paper metadata + summaries (not full body) |
| `get_paper_chunks` | Page full indexed body: `arxiv_id`, `limit` (default 20, max 50), `offset` |
| `search` | Hybrid passage search over indexed library |
| `request_topic_ingest` | **Admin HTTP only** — enqueue async search+ingest; returns `job_id` |
| `get_topic_ingest_job` | **HTTP** — poll job status (creator-only) |

Full paper via MCP:

1. `get_paper_chunks(arxiv_id, limit=20, offset=0)`
2. While `offset + returned < total`, set `offset += returned` and repeat.

Missing topic coverage (admin):

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_topic_jobs.sql
docker compose run --rm -T app python -m app.mcp_tokens create --label local-admin --role admin
docker compose up -d --build mcp mcp_worker
```

Then MCP: `request_topic_ingest(topic)` → poll `get_topic_ingest_job` until
`succeeded`/`failed`. Mint **admin** (not reader) for enqueue.

Never request PDF bytes from this server.

## 6. Failure cheat sheet

| Symptom | Fix |
|---------|-----|
| HTTP auth always fails | No active rows in `mcp_tokens` — mint again; old `MCP_TOKEN` env is ignored |
| `duplicate label` on create | `revoke --label ...` then create |
| stdio cannot reach DB | `docker compose up -d db`; app service uses `db:5432` |
| Tools missing `get_paper_chunks` | Rebuild image: `docker compose up -d --build mcp` (or rebuild `app`) |
| Rate limit 429 | Wait ~60s or raise `MCP_RATE_LIMIT_PER_MIN` |

## 7. Out of scope for this playbook

- Remote machine / TLS / reverse proxy
- OAuth
- Paper-level ACL
- Telegram bot auth (`ALLOWED_USERS`)

## See also

- Operator env notes: [configuration.md](configuration.md)
- Token feature quickstart: [`../specs/020-mcp-user-tokens/quickstart.md`](../specs/020-mcp-user-tokens/quickstart.md)
- Chunk paging feature: [`../specs/024-mcp-paper-chunks/spec.md`](../specs/024-mcp-paper-chunks/spec.md)
