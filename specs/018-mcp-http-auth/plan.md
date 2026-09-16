# Plan

Reuse the existing three tools. Add HTTP entrypoint:

`python -m app.mcp_server --http`

HTTP path:
- MCP SDK Streamable HTTP
- Bearer shared secret from `MCP_TOKEN` via `TokenVerifier`
- In-process per-IP rate limit middleware (default 60/min)
- Compose service `mcp` publishing port 8000

Stdio path unchanged (`python -m app.mcp_server`).

Env:
- `MCP_TOKEN` required for `--http`
- `MCP_HTTP_HOST` default `0.0.0.0`
- `MCP_HTTP_PORT` default `8000`
- `MCP_RATE_LIMIT_PER_MIN` default `60`
- `MCP_RESOURCE_URL` optional public resource URL for auth metadata

Verify with MCP HTTP client: 401 without token, tools with token, 429 under flood.
