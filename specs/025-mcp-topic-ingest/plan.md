# Plan: MCP Topic Ingest Jobs

## Technical Context

- Python as-built; Postgres jobs table; reuse `search_papers` / `save_paper` /
  `ingest_paper` / `enrich_and_save`
- MCP tools on existing HTTP + stdio server; **enqueue only with HTTP admin
  Bearer** (stdio has no credential identity)
- No new third-party libraries
- Worker: separate long-running process (Compose service), not inside MCP
  request handlers

## Constitution Check

| Principle | Status |
|-----------|--------|
| I Spec Kit | OK - `025-mcp-topic-ingest` |
| II MCP surface | **Amend 1.5.0 → 1.6.0**: allow admin-only MCP tools to enqueue durable topic ingest jobs and poll status; ingest work stays in a worker, not the MCP request thread; no PDF/`ask` |
| III Ingest integrity | OK - same ingest path; only `indexed` is "added" |
| V No duplicate pipelines | OK - reuse arxiv search + ingest |
| VI Schema gated | OK - `scripts/mcp_topic_jobs.sql` |

## Approach

### Schema (`scripts/mcp_topic_jobs.sql`)

Table `mcp_topic_jobs`:

| Column | Notes |
|--------|--------|
| id | bigserial PK |
| topic | text NOT NULL |
| status | `queued` \| `running` \| `succeeded` \| `failed` |
| creator_credential_id | bigint NULL REFERENCES mcp_tokens(id) |
| created_at / updated_at / finished_at | timestamptz |
| error | text NULL |
| found_count / indexed_count / failed_count | int NOT NULL default 0 |

Index: `(status, id)` for worker claim. Allow parallel jobs (no unique on topic).

### DB API (`app/db/mcp_topic_jobs.py`)

- `enqueue(topic, creator_credential_id) -> job`
- `get_job(job_id) -> job | None`
- `claim_next_queued() -> job | None` (UPDATE … WHERE status=queued ORDER BY id FOR UPDATE SKIP LOCKED)
- `mark_running` / `mark_succeeded(counts)` / `mark_failed(error)`

### Auth wiring

Extend `DbTokenVerifier` / `AccessToken` scopes to include `cred_id:{id}` and
`role:{role}` (already has role). Tool helpers resolve current credential from
request context if the SDK exposes it; if not, pass credential via a
contextvar set in a thin auth hook or look up Bearer again inside the tool
(same as rate-limit peek — acceptable).

Locks:

- `request_topic_ingest`: HTTP + role admin only
- `get_topic_ingest_job`: HTTP + job.creator_credential_id == caller id
- stdio: both tools return clear ToolError (`admin HTTP credential required`
  / `HTTP credential required`) — agent playbook already prefers HTTP

### MCP tools (`app/mcp_server.py`)

1. `request_topic_ingest(topic: str) -> {job_id, status, topic}`
   - topic strip; length 1..200; else ToolError
   - insert `queued`; return immediately
2. `get_topic_ingest_job(job_id: int) -> {…full status…}`
   - missing / wrong creator -> ToolError

### Worker (`python -m app.mcp_topic_worker`)

Loop (poll sleep 2s if idle):

1. `claim_next_queued` → `running`
2. `search_papers(topic, days=365, max_results=10)` (same defaults as bot `/search`)
3. For each hit: `save_paper`; if status needs ingest (`pending` / recoverable),
   run `ingest_paper` + `enrich_and_save` (sync via same functions as bot;
   honor `IngestBusyError` with limited retry/skip counted as failed)
4. Skip already `indexed`
5. `succeeded` with counts, or `failed` if search/setup explodes before any work
   (partial progress: still `succeeded` with failed_count > 0 unless zero found
   and hard error — prefer **succeeded** whenever the run finishes cleanly,
   even if some papers failed; **failed** only if the job cannot start/search)

Compose: service `mcp_worker` like `mcp`, `DATABASE_URL` to db, command
`python -m app.mcp_topic_worker`, depends_on db. No published ports.

### Docs

- `docs/configuration.md` + `.ru.md`: worker service + admin tools
- `docs/mcp-agent-connect.md` + `.ru.md`: mint **admin** token; poll loop
- system-overview tool list

## Verification

1. Admin HTTP: enqueue → job_id; get shows `queued`/`running` then terminal
2. Reader HTTP: enqueue ToolError
3. Creator-only: admin B cannot get admin A's job
4. Restart MCP HTTP: job row still gettable
5. Worker indexes ≥1 paper on a known topic (or found_count≥1 in dry lab)
6. Read tools still listed

## Non-goals

Webhooks; reader enqueue; sync wait; Telegram changes; new deps; PDF.
