# Feature Specification: MCP Topic Ingest Jobs

**Feature Branch**: `025-mcp-topic-ingest`  
**Created**: 2026-09-17  
**Status**: Verified

## Clarifications

### Session 2026-09-17

- Q: Delivery model → A: Async job (search + index); agent does not block on
  completion.
- Q: Notification → A: Poll job status via MCP tool (no webhook).
- Q: Who may request → A: Only MCP credentials with role `admin`.

## User Scenarios & Testing

### User Story 1 - Admin agent requests a missing topic (Priority: P1)

As an MCP admin client, when the library has little or no coverage for a
topic, I can submit an ingest job for that topic and receive a job id
immediately without waiting for indexing to finish.

**Independent Test**: As `admin`, call the request tool with a topic string.
Response includes a stable job id and an initial non-terminal status. The
call returns without waiting for papers to become `indexed`.

### User Story 2 - Agent learns when papers are ready (Priority: P1)

As the same client, I can poll the job until it reaches a terminal status and
see how many papers were indexed (or why it failed).

**Independent Test**: Poll the status tool with the job id. While work runs,
status is non-terminal. When finished successfully, status is terminal success
and reports counts; a forced failure path reports terminal failure with an
error summary. `reader` credentials cannot create jobs.

### User Story 3 - Readers keep read-only MCP (Priority: P1)

As a `reader` MCP client, I still use list/get/search/chunks tools, but I
cannot enqueue topic ingest.

**Independent Test**: `reader` Bearer calling the request tool is rejected with
an explicit authz error. Existing read tools still work.

### User Story 4 - Jobs survive process restarts (Priority: P2)

As an operator, job records are durable. After restarting MCP/HTTP, an
in-flight or queued job id remains queryable.

**Independent Test**: Create a job, restart the MCP HTTP process, poll the same
id; record still exists with a valid status.

## Requirements

- **FR-001**: MCP MUST provide an admin-only tool to enqueue a topic ingest
  job from a non-empty topic string and return a job id immediately.
- **FR-002**: A topic ingest job MUST asynchronously discover candidate papers
  for the topic and bring accepted papers to `indexed` in the shared library
  (search + ingest/enrich path), without blocking the enqueue call.
- **FR-003**: MCP MUST provide a tool to fetch job status by id, including at
  least: status, topic, timestamps, terminal error (if any), and summary
  counts of papers touched/indexed when available.
- **FR-004**: Only credentials with role `admin` MAY enqueue. Status fetch MAY
  be limited to jobs created by the same credential (or admin-readable — plan
  MUST pick one; default: creator-only).
- **FR-005**: `reader` and unauthenticated callers MUST NOT enqueue. Read-only
  tools from prior features MUST remain available.
- **FR-006**: Job state MUST be durable in the database (not only process
  memory).
- **FR-007**: Notification to the agent is by polling status; this feature
  MUST NOT require webhooks.
- **FR-008**: Enqueue MUST fail closed if no worker can be assumed? Prefer:
  enqueue always persists `queued`; a worker drains the queue (same host
  compose/bot/app — plan chooses). Empty topic / oversized topic MUST error.
- **FR-009**: No OAuth, no paper ACL, no PDF over MCP. No change to Telegram
  role matrix in this feature except optional operator docs cross-links.
- **FR-010**: No new third-party libraries without approval.

## Success Criteria

- **SC-001**: Admin enqueue returns a job id in under a few seconds without
  waiting for indexing.
- **SC-002**: Polling reaches a terminal success or failure for a completed
  job; success reflects indexed papers for that topic run.
- **SC-003**: Reader cannot enqueue.
- **SC-004**: Job id remains queryable after MCP process restart.
- **SC-005**: Existing read tools still function for admin and reader.

## Key Entities

- **Topic ingest job**: id, topic, status
  (`queued` | `running` | `succeeded` | `failed`), creator credential id,
  created/updated/finished timestamps, error text, counts (e.g. found,
  indexed, failed).

## Assumptions

- Owner defaults: async job + poll + admin-only.
- Worker runs on the same deployment as the library (Docker host), not inside
  the MCP request thread.
- "Added" means papers reach `ingest_status = 'indexed'` for that job's run.
- Duplicate active topic jobs: plan may coalesce or allow parallel; default
  allow parallel with distinct ids unless implement finds a simple unique
  constraint useful.

## Out of Scope

- Webhooks / push notifications.
- Reader self-serve ingest.
- MCP synchronous wait-until-indexed.
- Changing hybrid retrieval.
- OAuth / paper ACL.
- Replacing Telegram `/search` ingest UX (may coexist).
