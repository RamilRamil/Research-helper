import argparse
import os
import time
from collections import defaultdict, deque
from typing import Any

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AnyHttpUrl
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.db.mcp_tokens import lookup_active_by_raw, touch_last_used
from app.db.papers import get_indexed_paper, list_indexed_paper_chunks, list_indexed_papers

DEFAULT_RATE_LIMIT_PER_MIN = 60
DEFAULT_HTTP_HOST = "0.0.0.0"
DEFAULT_HTTP_PORT = 8000


class DbTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        try:
            cred = lookup_active_by_raw(token)
        except Exception:
            return None
        if cred is None:
            return None
        try:
            touch_last_used(cred.id)
        except Exception:
            pass
        return AccessToken(
            token=token,
            client_id=cred.label,
            scopes=["library:read", f"role:{cred.role}"],
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit_per_min: int) -> None:
        super().__init__(app)
        self._limit = limit_per_min
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _key(self, request: Request) -> str:
        host = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return f"ip:{host}"
        raw = auth.split(" ", 1)[1].strip()
        if not raw:
            return f"ip:{host}"
        try:
            cred = lookup_active_by_raw(raw)
        except Exception:
            return f"ip:{host}"
        if cred is None:
            return f"ip:{host}"
        return f"token:{cred.id}"

    async def dispatch(self, request: Request, call_next):
        key = self._key(request)
        now = time.monotonic()
        window = self._hits[key]
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
    def get_paper_chunks(
        arxiv_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Page through live indexed body chunks for one paper (full text)."""
        clean_id = (arxiv_id or "").strip()
        if not clean_id or len(clean_id) > 40:
            raise ToolError("arxiv_id must be a non-empty arXiv identifier")
        safe_limit = _bounded(limit, name="limit", minimum=1, maximum=50)
        safe_offset = _bounded(offset, name="offset", minimum=0, maximum=100000)
        try:
            page = list_indexed_paper_chunks(
                clean_id,
                limit=safe_limit,
                offset=safe_offset,
            )
        except Exception as exc:
            raise ToolError("Indexed paper chunks are unavailable") from exc
        if page is None:
            raise ToolError(f"Indexed paper not found: {clean_id}")
        return page

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
            "Use search for evidence passages, get_paper for metadata/summaries, "
            "get_paper_chunks to page through the indexed body text, and "
            "list_papers for discovery. This server never writes data."
        ),
        "version": "1.0.0",
    }
    if http_auth:
        host = (os.environ.get("MCP_HTTP_HOST") or DEFAULT_HTTP_HOST).strip()
        port = int(os.environ.get("MCP_HTTP_PORT") or DEFAULT_HTTP_PORT)
        resource = (
            os.environ.get("MCP_RESOURCE_URL") or f"http://{host}:{port}/mcp"
        ).strip()
        kwargs["token_verifier"] = DbTokenVerifier()
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
    import uvicorn

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
        help="Serve Streamable HTTP with DB bearer credentials",
    )
    args = parser.parse_args()
    if args.http:
        run_http()
        return
    server.run()


if __name__ == "__main__":
    main()
