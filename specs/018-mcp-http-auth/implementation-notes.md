# 018 implementation notes

## Done

- `app/mcp_server.py`: `--http` serves Streamable HTTP via
  `mcp.streamable_http_app` + uvicorn.
- Auth: `SharedTokenVerifier` + `AuthSettings` (`validate_token_resource=False`).
  Empty `MCP_TOKEN` fails closed at startup.
- Rate limit: in-process per-IP middleware (`MCP_RATE_LIMIT_PER_MIN`, default 60).
- Compose service `mcp` on `:8000`; `MCP_TOKEN` from project `.env` (compose
  interpolation). Do not leave `MCP_TOKEN: ${MCP_TOKEN}` unset on the host
  without a value in `.env` — blank interpolation overrides `env_file`.
- Stdio path unchanged (`python -m app.mcp_server` without `--http`).

## Verified (2026-09-16)

- HTTP initialize without Bearer -> `401`
- HTTP initialize with wrong Bearer -> `401`
- HTTP initialize with correct Bearer -> `200`
- MCP client `list_tools` + `list_papers` with token -> ok
- Flood -> `429`
- Stdio `list_tools` -> `get_paper`, `list_papers`, `search`

## Ops

- Public deploy: put TLS reverse proxy in front; app serves cleartext HTTP.
- Rotate `MCP_TOKEN` in `.env` for anything beyond local smoke.
