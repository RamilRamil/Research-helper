# Quickstart: MCP Topic Ingest Jobs

## 1. Migrate

```bash
docker compose exec -T db psql -U research -d research < scripts/mcp_topic_jobs.sql
```

## 2. Mint admin credential

```bash
docker compose run --rm -T app python -m app.mcp_tokens create --label agent-admin --role admin
```

## 3. Run HTTP MCP + worker

```bash
docker compose up -d --build mcp mcp_worker
```

## 4. From MCP client (Bearer admin)

1. `request_topic_ingest("your topic")` → `job_id`
2. Poll `get_topic_ingest_job(job_id)` until `succeeded` or `failed`
3. `search` / `get_paper_chunks` on new indexed ids

## 5. Reader check

Reader Bearer calling `request_topic_ingest` must error.
