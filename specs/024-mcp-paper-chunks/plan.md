# Plan: MCP Paper Chunks

## Approach

Add one tool: `get_paper_chunks(arxiv_id, limit=20, offset=0)`.

### Data

Reuse live chunks (`chunks.chunk_gen = papers.chunk_gen`) for
`ingest_status = 'indexed'` only.

`app/db/papers.py` (or `chunks.py`): `list_indexed_paper_chunks(arxiv_id, *, limit, offset) -> dict`
with `arxiv_id`, `title`, `chunks[{chunk_index, section, text}]`, `total`,
`limit`, `offset`, `returned`.

### MCP

Register in `app/mcp_server.py` beside existing tools. Bounds:
- `limit` 1..50 (default 20)
- `offset` 0..100000

Errors: unknown / not indexed -> `ToolError` (same style as `get_paper`).

### Docs

configuration + system-overview (EN/RU): four tools; quick note on paging.
Update `specs/README.md` / `RAG_UPGRADE_PLAN.md`.

### Constitution

Amend Principle II / feature map: MCP may expose `get_paper_chunks` in addition
to the three discovery/search tools (still read-only, no writes).

## Verification

1. Indexed paper: page0 + page1 cover contiguous indices; sum reaches `total`
2. Unknown id / pending id -> ToolError
3. `list_papers` / `get_paper` / `search` still register

## Non-goals

PDF, full blob, ACL, new deps.
