# Plan: MCP Per-User Tokens

## Technical Context

- **Language**: Python 3.12 (as-built image); type hints; ASCII string literals
- **Storage**: PostgreSQL (`DATABASE_URL`); new table via `scripts/mcp_tokens.sql`
- **HTTP**: existing MCP Streamable HTTP + Starlette middleware (`app/mcp_server.py`)
- **Crypto**: stdlib only (`secrets`, `hashlib`, `hmac.compare_digest`) - no new libs
- **Defaults**: rate limit 60/min (same env `MCP_RATE_LIMIT_PER_MIN`); last_used
  coalesce window **60s** in-process
- **Target**: replace shared `MCP_TOKEN` with DB credentials; stdio unchanged

## Constitution Check

| Principle | Status |
|-----------|--------|
| I Spec Kit path | OK - active `020-mcp-user-tokens` |
| II Knowledge Runtime / scope | **Amend 1.3.0 → 1.4.0**: allow DB per-user MCP HTTP credentials; keep OAuth / paper ACL / heterogeneous MCP clients out |
| III Ingest integrity | N/A (auth only) |
| IV Groundedness | N/A |
| V No duplicate pipelines | OK - same three tools / hybrid search |
| VI Deps and schema gated | OK - SQL in `scripts/`; no new packages |
| VII Eval not vibes | OK - verify matrix in Verification |

Gate: constitution amend ships in implement T001 before app code.

## Approach

### Schema

`scripts/mcp_tokens.sql`:

- table `mcp_tokens`
  - `id` bigserial PK
  - `label` text NOT NULL
  - `role` text NOT NULL CHECK (`admin` | `reader`)
  - `token_hash` text NOT NULL UNIQUE
  - `created_at` timestamptz NOT NULL default now()
  - `revoked_at` timestamptz NULL
  - `last_used_at` timestamptz NULL
- partial unique index on `label` WHERE `revoked_at IS NULL`

### Code

- `app/db/mcp_tokens.py`: create (gen secret + store hash), revoke by label,
  lookup active by hash, touch last_used (coalesced)
- Hash: `sha256` hex of raw token (high-entropy `secrets.token_urlsafe(32)`);
  verify with `hmac.compare_digest`
- `DbTokenVerifier(TokenVerifier)` in `app/mcp_server.py` (or tiny
  `app/mcp_auth.py`): Bearer → hash → active row → `AccessToken` with
  `client_id=label` (and role in scopes or client metadata as needed by SDK)
- Remove `SharedTokenVerifier` / `MCP_TOKEN` requirement
- HTTP fail-closed: zero active rows → verify always fails (process MAY start;
  no anonymous library access)
- `RateLimitMiddleware`: peek `Authorization: Bearer`; if verify succeeds use
  key `token:{id}`; else key `ip:{host}`. Same limit budget from env.
- last_used: after successful verify, UPDATE if `last_used_at` is null or older
  than 60s (SQL `WHERE` guard); in-process debounce optional to cut chatter

### Operator CLI

`python -m app.mcp_tokens create --label NAME --role reader|admin`  
→ prints raw secret once to stdout; stores hash only.

`python -m app.mcp_tokens revoke --label NAME`  
→ sets `revoked_at` on active row with that label.

No env import of old `MCP_TOKEN`.

### Docs / env

- Remove `MCP_TOKEN` from `.env.example` and configuration docs (EN/RU)
- Document mint/revoke + Bearer with directory credential
- Compose `mcp` service: still needs `DATABASE_URL`; drop `MCP_TOKEN`

### Cutover

1. Apply `scripts/mcp_tokens.sql`
2. Mint at least one credential
3. Point clients to new Bearer
4. Deploy HTTP without `MCP_TOKEN`
5. Remove leftover `MCP_TOKEN` from host `.env`

## Verification

1. Mint two labels; both HTTP tool calls OK; unknown Bearer rejected
2. Duplicate active label rejected at create
3. Revoke A; A fails; B OK; re-mint A with same label OK
4. `MCP_TOKEN` set in env does not authorize
5. Zero active rows → HTTP auth fails (no library data)
6. Flood without/invalid Bearer → 429 by IP; flood with token A → 429 for A
   while B on same IP still OK within budget
7. Stdio three tools without Bearer
8. After successful HTTP use, `last_used_at` advances; repeated calls within
   60s do not require a write every time

## Non-goals

OAuth, paper ACL, Telegram↔MCP merge, admin UI, operator-supplied secrets,
TTL/expiry, stdio Bearer, new MCP tools.
