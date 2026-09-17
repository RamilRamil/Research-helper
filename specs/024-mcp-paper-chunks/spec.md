# Feature Specification: MCP Paper Chunks

**Feature Branch**: `024-mcp-paper-chunks`  
**Created**: 2026-09-17  
**Status**: Verified

## Clarifications

### Session 2026-09-17

- Q: Full-paper delivery shape → A: Indexed chunks by arxiv_id with
  offset/limit paging (not PDF, not one giant blob).

## User Scenarios & Testing

### User Story 1 - Agent reads a paper in pages (Priority: P1)

As an MCP client agent, I can fetch the indexed body of one paper as ordered
chunks, page by page, until I have the full text I need.

**Independent Test**: For a known indexed paper, call the new tool with
`limit` small enough to require two pages. Page 0 and page 1 return contiguous
`chunk_index` ranges; `total` matches the paper's live chunk count.

### User Story 2 - Unknown / non-indexed papers fail clearly (Priority: P1)

As an MCP client, asking for chunks of a missing or non-indexed id must not
return empty success that looks like an empty paper.

**Independent Test**: Unknown id and a non-indexed id produce explicit tool
errors.

### User Story 3 - Existing tools stay (Priority: P2)

As an operator, `list_papers`, `get_paper`, and `search` keep their current
contracts. Stdio and HTTP auth from `020` stay unchanged.

**Independent Test**: Tool list includes the previous three plus the new
chunks tool; metadata `get_paper` still omits full body.

## Requirements

- **FR-001**: MCP MUST expose a read-only tool that returns ordered live-generation
  chunks for one indexed paper by arXiv id.
- **FR-002**: Results MUST be pageable via `limit` and `offset`, validated
  server-side with explicit bounds.
- **FR-003**: Each chunk MUST include `chunk_index`, optional `section`, and
  `text`. Results MUST omit embeddings, DB UUIDs, paths, and ingest internals.
- **FR-004**: Response MUST include enough pagination metadata for a client to
  walk the whole paper (`total`, `limit`, `offset`, `returned`).
- **FR-005**: Only `ingest_status = 'indexed'` papers are readable; others
  MUST error explicitly.
- **FR-006**: The tool MUST NOT mutate data and MUST NOT add a second retrieval
  stack.
- **FR-007**: Existing three tools MUST remain available with unchanged
  contracts in this feature.
- **FR-008**: No PDF bytes, no filesystem paths, no new third-party libraries.

## Success Criteria

- **SC-001**: An agent can retrieve all live chunks of an indexed paper by
  repeating the tool with increasing offsets until `offset + returned >= total`.
- **SC-002**: Missing or non-indexed ids produce explicit errors.
- **SC-003**: Chunk pages are ordered by ascending `chunk_index` with no gaps
  inside a page relative to the live generation.
- **SC-004**: `list_papers` / `get_paper` / `search` still work as before.

## Assumptions

- Owner chose chunk paging over single full-text blob and over PDF.
- Live `papers.chunk_gen` defines which chunk rows are current.
- Default page size is plan-default (20); max page size plan-default (50).

## Out of Scope

- PDF download / binary transfer.
- Changing hybrid `search`.
- Paper ACL / per-user corpus.
- Write tools / `/ask` over MCP.
- Re-embedding or reindex from MCP.
