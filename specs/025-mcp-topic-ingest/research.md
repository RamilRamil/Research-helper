# Research: MCP Topic Ingest Jobs

## Decision: Durable Postgres jobs + separate worker process

- **Rationale**: Spec requires restart-safe status and non-blocking enqueue.
  Process-local FIFO (`reindex_queue`) dies on restart and couples to Telegram.
- **Alternatives**: In-MCP background asyncio task; reuse bot reindex queue.

## Decision: Compose service `mcp_worker`

- **Rationale**: Keeps Streamable HTTP handlers thin; same image as app/mcp;
  easy `docker compose up`.
- **Alternatives**: Drain inside `mcp` process; cron; Telegram bot side-car.

## Decision: Creator-only job status visibility

- **Rationale**: Spec default; least surprise for multi-admin later.
- **Alternatives**: Any admin can read any job.

## Decision: Enqueue/get require HTTP credential (stdio rejected)

- **Rationale**: Role/cred_id only exist after Bearer verify; stdio is anonymous
  host trust and would bypass admin gate or invent a fake principal.
- **Alternatives**: Treat stdio as implicit admin (rejected — too wide).

## Decision: Parallel jobs allowed; worker claims one at a time

- **Rationale**: Simple SKIP LOCKED FIFO; avoids topic unique races; ingest
  already has per-paper locks.
- **Alternatives**: One active job per topic; multi-threaded worker.

## Decision: Job `succeeded` if run completes; per-paper failures in counts

- **Rationale**: Agent cares that the attempt finished and how many indexed;
  one bad PDF should not hide partial success.
- **Alternatives**: Fail entire job if any paper fails.

## Decision: Constitution 1.6.0

- **Rationale**: Principle II still forbids MCP write/ingest tools; this feature
  adds admin enqueue + poll only, with worker doing ingest.
- **Alternatives**: Violate constitution (forbidden).
