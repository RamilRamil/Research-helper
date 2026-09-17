# Tasks: MCP Per-User Tokens

**Feature**: `020-mcp-user-tokens`  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

## Dependencies

```text
Phase 1 Setup -> Phase 2 Foundational
  -> US1 (credentials + HTTP auth)
  -> US2 (revoke) [needs US1]
  -> US3 (no shared env token) [needs US1]
  -> US4 (dual rate limit) [needs US1]
  -> US5 (stdio) [parallel after foundational; verify after US1]
  -> US6 (empty fail-closed) [needs US1]
  -> Polish
```

MVP: Phase 1–2 + US1 (mint two credentials, HTTP tools work, unknown rejected).

## Phase 1: Setup

- [x] T001 Confirm constitution `1.4.0` in `.specify/memory/constitution.md` and
      active `.specify/feature.json` -> `specs/020-mcp-user-tokens`.

## Phase 2: Foundational

- [x] T002 Create `scripts/mcp_tokens.sql` (`mcp_tokens` table + partial unique
      index on active `label` + unique `token_hash`) per `data-model.md`.
- [x] T003 Implement `app/db/mcp_tokens.py`: generate secret, SHA-256 hash,
      create/revoke/lookup active by hash, coalesced `last_used_at` (60s).
- [x] T004 Implement CLI `app/mcp_tokens.py` (`python -m app.mcp_tokens`
      create/revoke) printing raw secret once; ASCII errors; no env import.

## Phase 3: US1 - Per-client HTTP credentials (P1)

**Goal**: Distinct DB credentials authorize HTTP MCP tools on shared library.  
**Test**: Mint two labels; both call a tool; unknown Bearer rejected; duplicate
active label rejected at create.

- [x] T005 [US1] Add `DbTokenVerifier` and wire HTTP auth in
      `app/mcp_server.py` (Bearer -> hash -> active row -> `AccessToken`).
- [x] T006 [US1] Remove `SharedTokenVerifier` and any `MCP_TOKEN` auth path
      from `app/mcp_server.py`.

## Phase 4: US2 - Revoke one client (P1)

**Goal**: Revoke blocks only that credential.  
**Test**: Revoke A; A fails; B OK; re-mint same label OK.

- [x] T007 [US2] Verify revoke via CLI + HTTP in practice; fix
      `app/db/mcp_tokens.py` / verifier if revoked rows still match.

## Phase 5: US3 - Shared env token gone (P1)

**Goal**: Former env secret never authorizes and is not imported.  
**Test**: `MCP_TOKEN` set/unset does not grant access; only directory creds work.

- [x] T008 [P] [US3] Remove `MCP_TOKEN` from `.env.example` and drop it from
      `docker-compose.yml` mcp service if present.
- [x] T009 [P] [US3] Update `docs/configuration.md` +
      `docs/configuration.ru.md` for mint/revoke + Bearer (no shared token).

## Phase 6: US4 - Dual rate limits (P1)

**Goal**: IP key before identity; token id key after verify.  
**Test**: Flood invalid -> 429 by IP; flood token A -> 429 for A; B on same IP
still within budget.

- [x] T010 [US4] Update `RateLimitMiddleware` in `app/mcp_server.py` for
      `ip:{host}` vs `token:{id}` keys per plan/contract.

## Phase 7: US5 - Stdio unchanged (P2)

**Goal**: Stdio three tools without Bearer.  
**Test**: `python -m app.mcp_server` lists/calls tools without auth.

- [x] T011 [US5] Confirm stdio `build_server(http_auth=False)` path in
      `app/mcp_server.py` stays token-free; fix regressions if any.

## Phase 8: US6 - Empty directory fail-closed (P2)

**Goal**: Zero active credentials => no library over HTTP.  
**Test**: HTTP with empty table rejects auth; no tool data.

- [x] T012 [US6] Ensure verifier rejects all when no active rows
      (`app/db/mcp_tokens.py` / `app/mcp_server.py`); process MAY still start.

## Phase 9: Polish

- [x] T013 [P] Sync `docs/system-overview.md` + `.ru.md` MCP auth wording if
      they still say shared `MCP_TOKEN`.
- [x] T014 Run plan Verification matrix (mint/revoke/env/rate/stdio/last_used);
      mark `specs/README.md` + `RAG_UPGRADE_PLAN.md` verified for `020`.

## Parallel examples

- After T004: T008 || T009 (docs/env) once T006 done for accurate docs.
- After T006: T007, T010, T011, T012 can proceed with care (T010 touches same
  middleware file as auth - serialize with T005/T006).
- T013 || T014 only after code complete.

## Strategy

1. Ship foundational SQL + CLI first (can mint before HTTP wired).
2. MVP = US1 HTTP auth.
3. Then revoke, env removal, dual rate limit, empty/stdio checks, docs status.
