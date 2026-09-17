# Research: MCP Per-User Tokens

## Decision: Store credentials in PostgreSQL

- **Rationale**: Owner wants a growing user directory with revoke without
  restart; env lists do not scale; file store is a weak middle ground.
- **Alternatives**: `ALLOWED_USERS`-style env; secrets file on disk.

## Decision: Hard-remove shared `MCP_TOKEN` (no import)

- **Rationale**: One auth path; do not promote a possibly leaked shared secret
  into a long-lived DB row. Cutover = mint fresh then switch clients.
- **Alternatives**: Legacy accept env token; one-shot import when table empty.

## Decision: SHA-256 hash of high-entropy token (stdlib)

- **Rationale**: Tokens are `token_urlsafe(32)`; unsalted SHA-256 is enough for
  API secrets of that entropy; no new crypto libraries (constitution VI).
- **Alternatives**: bcrypt/argon2 (new dep); HMAC with server pepper env
  (extra secret to manage for little gain here).

## Decision: Partial unique index on active `label`

- **Rationale**: Clarification - unique among active; reuse after revoke.
- **Alternatives**: Global unique forever; labels non-unique.

## Decision: Dual rate-limit keys in one middleware

- **Rationale**: Spec requires IP before identity and token after verify;
  keep single limiter and existing `MCP_RATE_LIMIT_PER_MIN` default 60.
- **Alternatives**: IP-only; token-only; separate numeric budgets.

## Decision: last_used coalesce 60s

- **Rationale**: Clarify chose windowed updates; 60s matches rate-limit window
  and keeps writes cheap.
- **Alternatives**: Every request; no last_used.

## Decision: HTTP may boot with zero tokens; verify fails closed

- **Rationale**: Operator can mint via CLI against DB then use HTTP without
  restarting for "first token" if process already up; empty directory never
  serves library data.
- **Alternatives**: Refuse to start `--http` when count=0 (forces restart after
  first mint).

## Decision: Constitution 1.4.0

- **Rationale**: Principle II still listed per-user MCP tokens as out of scope;
  this feature is the separate spec that lifts only that item.
- **Alternatives**: Ignore constitution (forbidden).
