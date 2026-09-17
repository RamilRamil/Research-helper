# Contract: MCP topic ingest tools (025)

## Tools

### `request_topic_ingest`

| Input | Rules |
|-------|--------|
| `topic` | string, strip; length 1..200 |

| Output | |
|--------|--|
| `job_id` | int |
| `status` | `"queued"` |
| `topic` | normalized topic |

Auth: HTTP Bearer with role `admin`. Otherwise ToolError.

### `get_topic_ingest_job`

| Input | Rules |
|-------|--------|
| `job_id` | positive int |

| Output | |
|--------|--|
| `job_id` | int |
| `topic` | string |
| `status` | queued \| running \| succeeded \| failed |
| `created_at` / `updated_at` / `finished_at` | ISO-8601 or null |
| `error` | string or null |
| `found_count` / `indexed_count` / `failed_count` | int |

Auth: HTTP Bearer; caller credential must own the job. Missing job or wrong
owner → ToolError.

## Agent poll loop

```text
r = request_topic_ingest(topic)
loop:
  j = get_topic_ingest_job(r.job_id)
  if j.status in (succeeded, failed): break
  sleep ~5s
```

## Worker

Separate process claims `queued` rows and performs search + ingest. Not part of
the MCP HTTP request path.
