# Data Model: MCP Per-User Tokens

## Entity: MCP credential (`mcp_tokens`)

| Field | Type | Rules |
|-------|------|--------|
| id | bigserial | PK |
| label | text | required; unique among rows with `revoked_at IS NULL` |
| role | text | `admin` or `reader` only |
| token_hash | text | required; unique; SHA-256 hex of raw secret |
| created_at | timestamptz | default now() |
| revoked_at | timestamptz | null = active |
| last_used_at | timestamptz | null until first successful HTTP auth |

## State transitions

```text
(mint) -> active
active -> revoked  (revoke by label; sets revoked_at)
revoked -> (terminal for that row)
(mint same label) -> new active row  (allowed after prior revoke)
```

No time-based expiry transition.

## Validation

- Create rejects unknown role
- Create rejects if an active row already has the label
- Lookup for auth: match `token_hash` AND `revoked_at IS NULL` only
- Revoke no-ops or errors clearly if no active label (plan: clear error)

## Relationships

- No FK to papers/users. Shared library unchanged.
- Telegram allowlist remains separate (no join in this feature).

## Indexes

- UNIQUE (`token_hash`)
- UNIQUE (`label`) WHERE `revoked_at IS NULL`
