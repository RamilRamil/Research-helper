# Quickstart: MCP Per-User Tokens

## 1. Migrate

```bash
psql "$DATABASE_URL" -f scripts/mcp_tokens.sql
```

## 2. Mint a credential

```bash
python -m app.mcp_tokens create --label alice --role reader
```

Save the printed secret; it will not be shown again.

## 3. Run HTTP MCP

```bash
python -m app.mcp_server --http
```

Do not set `MCP_TOKEN`. Ensure `DATABASE_URL` reaches the same DB.

## 4. Call with Bearer

```bash
# Example: MCP client or curl against your MCP HTTP URL
Authorization: Bearer <raw_secret_from_mint>
```

## 5. Revoke

```bash
python -m app.mcp_tokens revoke --label alice
```

## 6. Stdio (unchanged)

```bash
python -m app.mcp_server
```

No Bearer required on the host.
