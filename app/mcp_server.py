import argparse
import os
import secrets
import time
from collections import defaultdict, deque
from typing import Any

import uvicorn
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AnyHttpUrl
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.db.papers import get_indexed_paper, list_indexed_papers

DEFAULT_RATE_LIMIT_PER_MIN = 60
DEFAULT_HTTP_HOST = "0.0.0.0"
DEFAULT_HTTP_PORT = 8000


class SharedTokenVerifier(TokenVerifier):
    def __init__(self, token: str) -> None:
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or not secrets.compare_digest(token, self._token):
            return None
        return AccessToken(
            token=token,
            client_id="shared",
            scopes=["library:read"],
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit_per_min: int) -> None:
        super().__init__(app)
        self._limit = limit_per_min
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client]
        while window and now - window[0] >= 60.0:
            window.popleft()
        if len(window) >= self._limit:
            return JSONResponse(
                {"error": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return await call_next(request)


def _bounded(value: int, *, name: str, minimum: int, maximum: int) -> int:
    if value < minimum or value > maximum:
        raise ToolError(f"{name} must be between {minimum} and {maximum}")
    return value


def _register_tools(mcp: MCPServer) -> None:
    @mcp.tool(structured_output=True)
    def list_papers(limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """List safe metadata for indexed papers, newest first."""
        safe_limit = _bounded(limit, name="limit", minimum=1, maximum=100)
        safe_offset = _bounded(offset, name="offset", minimum=0, maximum=10000)
        try:
            papers = list_indexed_papers(limit=safe_limit, offset=safe_offset)
        except Exception as exc:
            raise ToolError("Indexed paper list is unavailable") from exc
        return {
            "papers": papers,
            "limit": safe_limit,
            "offset": safe_offset,
            "returned": len(papers),
        }

    @mcp.tool(structured_output=True)
    def get_paper(arxiv_id: str) -> dict[str, Any]:
        """Get safe metadata and summaries for one indexed arXiv paper."""
        clean_id = (arxiv_id or "").strip()
        if not clean_id or len(clean_id) > 40:
            raise ToolError("arxiv_id must be a non-empty arXiv identifier")
        try:
            paper = get_indexed_paper(clean_id)
        except Exception as exc:
            raise ToolError("Indexed paper lookup is unavailable") from exc
        if paper is None:
            raise ToolError(f"Indexed paper not found: {clean_id}")
        return paper

    @mcp.tool(structured_output=True)
    def search(query: str, limit: int = 5) -> dict[str, Any]:
        """Search indexed passages with the existing hybrid retrieval pipeline."""
        clean_query = (query or "").strip()
        if not clean_query:
            raise ToolError("query must not be empty")
        if len(clean_query) > 500:
            raise ToolError("query must be at most 500 characters")
        safe_limit = _bounded(limit, name="limit", minimum=1, maximum=10)
        try:
            from app.db.search import hybrid_search

            hits = hybrid_search(
                clean_query,
                limit=safe_limit,
                fetch_k=max(20, safe_limit * 4),
            )
        except Exception as exc:
            if "embed quota:" in str(exc):
                raise ToolError(
                    "Search unavailable: query embedding quota exhausted"
                ) from exc
            raise ToolError("Hybrid search is unavailable") from exc
        passages = [
            {
                "arxiv_id": hit.get("arxiv_id"),
                "title": hit.get("title"),
                "section": hit.get("section"),
                "text": hit.get("text") or hit.get("snippet") or "",
                "source": hit.get("source"),
                "rrf_score": hit.get("rrf_score"),
            }
            for hit in hits
        ]
        return {
            "query": clean_query,
            "passages": passages,
            "returned": len(passages),
        }


def build_server(*, http_auth: bool = False) -> MCPServer:
    kwargs: dict[str, Any] = {
        "name": "research-library",
        "description": "Read-only access to the indexed arXiv paper library.",
        "instructions": (
            "Use search for evidence passages, get_paper for one indexed paper, "
            "and list_papers for discovery. This server never writes data."
        ),
        "version": "1.0.0",
    }
    if http_auth:
        token = (os.environ.get("MCP_TOKEN") or "").strip()
        if not token:
            raise RuntimeError("MCP_TOKEN required for HTTP mode")
        host = (os.environ.get("MCP_HTTP_HOST") or DEFAULT_HTTP_HOST).strip()
        port = int(os.environ.get("MCP_HTTP_PORT") or DEFAULT_HTTP_PORT)
        resource = (
            os.environ.get("MCP_RESOURCE_URL") or f"http://{host}:{port}/mcp"
        ).strip()
        kwargs["token_verifier"] = SharedTokenVerifier(token)
        kwargs["auth"] = AuthSettings(
            issuer_url=AnyHttpUrl("https://local.token/"),
            resource_server_url=AnyHttpUrl(resource),
            required_scopes=["library:read"],
            validate_token_resource=False,
        )
    mcp = MCPServer(**kwargs)
    _register_tools(mcp)
    return mcp


# Stdio hosts import this module-level server.
server = build_server(http_auth=False)


def _rate_limit() -> int:
    raw = (os.environ.get("MCP_RATE_LIMIT_PER_MIN") or "").strip()
    if not raw:
        return DEFAULT_RATE_LIMIT_PER_MIN
    value = int(raw)
    if value < 1:
        raise RuntimeError("MCP_RATE_LIMIT_PER_MIN must be >= 1")
    return value


def run_http() -> None:
    host = (os.environ.get("MCP_HTTP_HOST") or DEFAULT_HTTP_HOST).strip()
    port = int(os.environ.get("MCP_HTTP_PORT") or DEFAULT_HTTP_PORT)
    mcp = build_server(http_auth=True)
    app = mcp.streamable_http_app(host=host)
    app.add_middleware(RateLimitMiddleware, limit_per_min=_rate_limit())
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(description="Research library MCP server")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve Streamable HTTP with bearer token auth",
    )
    args = parser.parse_args()
    if args.http:
        run_http()
        return
    server.run()


if __name__ == "__main__":
    main()
