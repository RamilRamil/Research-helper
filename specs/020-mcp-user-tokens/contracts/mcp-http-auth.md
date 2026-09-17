# Contract: MCP HTTP auth (020)

## Transport

- Streamable HTTP MCP endpoint (unchanged path from `018`)
- Auth header: `Authorization: Bearer <raw_secret>`
- Raw secret is shown once at mint; never stored in DB

## Auth outcomes

| Condition | Result |
|-----------|--------|
| Missing/invalid/revoked Bearer | Auth failure (no tool access) |
| Valid active credential | Tools: `list_papers`, `get_paper`, `search` (shared library) |
| Zero active credentials | All HTTP callers fail auth |
| Former `MCP_TOKEN` env alone | MUST NOT authorize |

## Rate limit

- Status `429` with explicit rate-limit error body (keep `018` shape)
- Unverified / failed auth traffic counted under client IP key
- Verified traffic counted under credential id key
- Default budget: 60 requests / 60s (`MCP_RATE_LIMIT_PER_MIN`)

## Operator CLI (stdout contract)

### Create

```text
python -m app.mcp_tokens create --label <label> --role <admin|reader>
```

Stdout includes the raw secret exactly once (ASCII). Exit non-zero on
duplicate active label or bad role.

### Revoke

```text
python -m app.mcp_tokens revoke --label <label>
```

Revokes the active credential with that label. Exit non-zero if none active.

## Stdio

Unaffected: no Bearer required; same three tools.
