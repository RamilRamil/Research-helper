# Feature Specification: Agentic Query Routing

**Feature Branch**: `005-query-routing`  
**Created**: 2026-09-09  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Compare questions use synthesis on purpose (Priority: P1)

As bot owner, a comparison `/ask` is routed to multi-paper synthesis even if I
do not use the old keyword list.

**Why this priority**: regex misses paraphrases and RU/EN mix.

**Independent Test**: Ask to compare two methods without the word "compare" if
possible, or a clear comparison. Bot thinking line shows `synthesis`.

**Acceptance Scenarios**:

1. **Given** a question that needs several papers, **when** `/ask` runs, **then**
   the announced route is `synthesis`.
2. **Given** a single-paper fact question, **when** `/ask` runs, **then** the
   route is `point`.

---

### User Story 2 - Identifier questions can use lexical retrieve (Priority: P2)

As bot owner, a question that is mainly an arXiv id or exact token may use
full-text first stage instead of hybrid.

**Acceptance Scenarios**:

1. **Given** the planner chooses `fts`, **when** point `/ask` retrieves, **then**
   the first stage is full-text, then the same rerank/CRAG gates.
2. **Given** the planner chooses `hybrid` or omits tool, **when** point `/ask`
   retrieves, **then** hybrid remains the first stage.

---

### User Story 3 - No regex fallback (Priority: P1)

As bot owner, routing is one LLM decision. If that call fails, I see an error,
not a silent keyword route.

**Acceptance Scenarios**:

1. **Given** the router model call fails, **when** `/ask` ends, **then** an
   error is shown and synthesis is not chosen by regex.

---

## Requirements

- **FR-001**: System MUST classify `/ask` as `point` or `synthesis` using the
  existing Gemini generate client (JSON).
- **FR-002**: System MUST NOT use the previous keyword regex as a backup.
- **FR-003**: Classifier MAY set retrieve tool `hybrid` or `fts` for `point`.
  Default `hybrid`. `synthesis` ignores `fts` (still hybrid per subquestion).
- **FR-004**: CRAG/rerank gates stay on the point path.
- **FR-005**: No LangGraph, no new packages, no graph index.

## Success Criteria

- **SC-001**: Thinking line shows `synthesis` for a comparison question.
- **SC-002**: Thinking line shows `point` for a single-id fact question.
- **SC-003**: Router failure does not silently become regex synthesis.

## Assumptions

- One extra generate call per `/ask` for routing.
- Graph / SQL / web tools wait for later specs.

## Out of Scope

- GraphRAG, Ragas, MCP, replacing CRAG.
- Deleting `decompose_question` (stays inside synthesis).
