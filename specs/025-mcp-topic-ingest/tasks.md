# Tasks: MCP Topic Ingest Jobs

**Feature**: `025-mcp-topic-ingest`  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

## Dependencies

```text
Setup -> Foundational (SQL + DB API + auth context)
  -> US1 enqueue (admin)
  -> US2 poll status (needs US1)
  -> US3 reader denied (with US1)
  -> Worker drain (enables US2 terminal)
  -> US4 durability check
  -> Polish (compose/docs/verify)
```

MVP: foundational + US1 enqueue + worker + US2 poll to terminal.

## Phase 1: Setup

- [x] T001 Confirm constitution `1.6.0` and `.specify/feature.json` ->
      `specs/025-mcp-topic-ingest`.

## Phase 2: Foundational

- [x] T002 Create `scripts/mcp_topic_jobs.sql` per `data-model.md`.
- [x] T003 Implement `app/db/mcp_topic_jobs.py` (enqueue, get_job,
      claim_next_queued SKIP LOCKED, mark_running/succeeded/failed).
- [x] T004 Extend `DbTokenVerifier` in `app/mcp_server.py` with `cred_id:{id}`
      scope (keep `role:{role}`); add helper to resolve caller cred from
      Bearer/contextvar for tools.

## Phase 3: US1 - Admin enqueue (P1)

- [x] T005 [US1] Add `request_topic_ingest` tool in `app/mcp_server.py`
      (admin HTTP only; topic 1..200; insert queued).

## Phase 4: US2 - Poll status (P1)

- [x] T006 [US2] Add `get_topic_ingest_job` tool in `app/mcp_server.py`
      (creator-only).

## Phase 5: Worker (enables terminal US2)

- [x] T007 Implement `app/mcp_topic_worker.py` (`python -m app.mcp_topic_worker`)
      per plan loop (search_papers 10/365, save, ingest+enrich, skip indexed).
- [x] T008 Add Compose service `mcp_worker` in `docker-compose.yml`.

## Phase 6: US3 - Reader denied (P1)

- [x] T009 [US3] Verify reader gate on enqueue; fix auth helper if needed.

## Phase 7: US4 - Durability (P2)

- [x] T010 [US4] Confirm jobs are DB-only (no process memory); note in
      quickstart if restart test is manual.

## Phase 8: Polish

- [x] T011 [P] Update `docs/configuration.md` + `.ru.md` (worker + admin tools).
- [x] T012 [P] Update `docs/mcp-agent-connect.md` + `.ru.md` (admin mint + poll
      loop) and system-overview tool list EN/RU.
- [x] T013 Run plan Verification matrix; mark `specs/README.md` +
      `RAG_UPGRADE_PLAN.md` verified for `025`.
