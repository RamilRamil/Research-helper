# Data Model: MCP Topic Ingest Jobs

## Entity: Topic ingest job (`mcp_topic_jobs`)

| Field | Type | Rules |
|-------|------|--------|
| id | bigserial | PK; job id returned to agent |
| topic | text | required; 1..200 chars after strip |
| status | text | `queued` \| `running` \| `succeeded` \| `failed` |
| creator_credential_id | bigint NULL | FK `mcp_tokens.id`; set at enqueue |
| created_at | timestamptz | default now() |
| updated_at | timestamptz | bumped on transitions |
| finished_at | timestamptz NULL | set on terminal |
| error | text NULL | set on `failed` |
| found_count | int | papers returned by search |
| indexed_count | int | newly reached `indexed` this run |
| failed_count | int | ingest/enrich failures this run |

## State transitions

```text
(enqueue) -> queued
queued -> running     (worker claim)
running -> succeeded  (clean finish)
running -> failed     (cannot search / fatal before useful work)
```

No cancel in this feature.

## Relationships

- `creator_credential_id` → `mcp_tokens.id` (ON DELETE SET NULL)
- Papers linked only by normal `found_by` / library rows; no job_id FK on
  papers in this slice.

## Indexes

- `(status, id)` for claim query
