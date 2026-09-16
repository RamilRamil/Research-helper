# Feature Specification: Read-Only MCP Library Server

**Feature Branch**: `017-mcp-library-server`  
**Created**: 2026-09-16  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Local agents discover indexed papers (Priority: P1)

As the library owner, I can connect a local MCP host and list indexed papers
without granting write access to the database.

**Independent Test**: Connect over stdio and call `list_papers`. The result
contains only indexed paper ids and safe metadata.

**Acceptance Scenarios**:

1. **Given** indexed and non-indexed papers, **when** `list_papers` is called,
   **then** only indexed papers are returned.
2. **Given** pagination inputs, **when** papers are listed, **then** the result
   is bounded and deterministic.

### User Story 2 - Local agents inspect one paper (Priority: P1)

As the library owner, I can retrieve the metadata and summaries for one
indexed paper by arXiv id.

**Independent Test**: Call `get_paper` with a known indexed id and an unknown
id. The known paper is returned; the unknown paper is reported clearly.

### User Story 3 - Local agents search paper passages (Priority: P1)

As the library owner, I can search the existing hybrid index and receive
bounded evidence passages with paper ids.

**Independent Test**: Call `search` with a supported query. Each result
contains an arXiv id, title, section, passage text, and retrieval score.

## Requirements

- **FR-001**: The server MUST expose exactly three read-only tools:
  `list_papers`, `get_paper`, and `search`.
- **FR-002**: All tools MUST only expose papers whose ingest status is
  `indexed`.
- **FR-003**: `search` MUST reuse the existing hybrid retrieval path and MUST
  NOT create a second index or retrieval pipeline.
- **FR-004**: Tool results MUST omit secrets, local filesystem paths, database
  identifiers, ingest errors, and mutable internal state.
- **FR-005**: Inputs and outputs MUST be bounded. List and search limits MUST
  be validated server-side.
- **FR-006**: The transport MUST be local stdio. The server MUST NOT listen on
  a network port.
- **FR-007**: The MCP process MUST keep stdout reserved for protocol messages.
- **FR-008**: The server MUST NOT expose ask, ingest, enrich, reindex, delete,
  update, SQL, or arbitrary file tools.
- **FR-009**: The official owner-approved Python MCP SDK MUST be exactly
  pinned with the rest of the application dependencies.

## Success Criteria

- **SC-001**: A real MCP client can initialize the server, discover exactly
  three tools, and call each tool successfully.
- **SC-002**: No tool call mutates paper or chunk records.
- **SC-003**: `list_papers` returns at most 100 papers and `search` returns at
  most 10 passages per call.
- **SC-004**: Unknown paper ids and unavailable search dependencies produce
  explicit tool errors rather than empty success or process termination.
- **SC-005**: A clean application image rebuild succeeds with exact dependency
  pins.

## Assumptions

- Local MCP hosts launch the server as a subprocess on the same machine.
- PostgreSQL is reachable through `DATABASE_URL`.
- Hybrid search still requires the existing Gemini query embedding.
- Public Streamable HTTP is a future feature, not a hidden mode in this one.

## Out of Scope

- Public or private network transport, authentication, TLS, rate limits.
- MCP client behavior and heterogeneous external sources.
- Generated answers (`ask`) and every write operation.
- Resources and prompts; this slice exposes tools only.
