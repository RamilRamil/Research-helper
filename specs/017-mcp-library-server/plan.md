# Implementation Plan: Read-Only MCP Library Server

## Technical Context

- Runtime: Python 3.12 in the existing application image.
- SDK: official `mcp==2.2.0`, owner-approved.
- Transport: stdio only.
- Store: existing PostgreSQL/pgvector database via `DATABASE_URL`.
- Retrieval: existing `app.db.search.hybrid_search`.
- Packaging: one module, `app.mcp_server`; no new top-level directory.

## Constitution Check

- Spec Kit path: PASS. `017` owns all app/dependency/doc changes.
- One thin slice: PASS. Read-only library exposure only.
- Indexed-only retrieval: PASS.
- No duplicate pipeline: PASS. Search delegates to `hybrid_search`.
- Dependency gate: PASS. Owner approved the official MCP SDK.
- MCP scope: PASS after constitution 1.1.0 amendment.

## Design

- Add bounded read helpers to `app.db.papers`:
  - list indexed paper metadata with `limit` and `offset`;
  - get one indexed paper by normalized arXiv id.
- Add `app.mcp_server` with one module-level `MCPServer`.
- Register exactly three synchronous tools:
  - `list_papers(limit=50, offset=0)`;
  - `get_paper(arxiv_id)`;
  - `search(query, limit=5)`.
- Validate bounds before touching dependencies.
- Return JSON-compatible dictionaries only. Do not return UUIDs, local paths,
  ingest errors, or database connection details.
- Let MCP encode tool failures; convert expected missing/dependency failures to
  concise errors without secrets.
- Run with `python -m app.mcp_server`; default `mcp.run()` is stdio.

## Verification

1. Build the app image from exact pins.
2. Use the official MCP client over stdio to initialize and list tools.
3. Assert tool names are exactly `get_paper`, `list_papers`, and `search`.
4. Call all three against the live indexed library.
5. Confirm invalid limits and unknown ids are explicit errors.
6. Confirm no network listener or write tool exists.

## Future

A separate feature may serve the same tool surface via Streamable HTTP. It must
design authentication, authorization, TLS termination, rate limits, deployment,
and audit logging before the constitution permits public network transport.
