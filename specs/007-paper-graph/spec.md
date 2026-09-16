# Feature Specification: Paper Graph Hop

**Feature Branch**: `007-paper-graph`  
**Created**: 2026-09-10  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Theme questions pull related papers (Priority: P1)

As bot owner, a library-wide or "related work" `/ask` uses papers linked by
shared tags to the first retrieval hits, not only the hybrid top list.

**Why this priority**: vector search misses multi-hop neighbors. Full GraphRAG
(Leiden, community summaries) needs new libraries; this slice uses existing
`papers.tags`.

**Independent Test**: Ask a themes/across-library question. Thinking line
shows `graph`. Sources may include a paper not in a naive top-5 hybrid of the
same wording.

**Acceptance Scenarios**:

1. **Given** a global/theme question, **when** `/ask` runs, **then** route is
   `graph`.
2. **Given** seed indexed papers have tags overlapping other indexed papers,
   **when** graph retrieve runs, **then** neighbor paper ids can appear in the
   ranked pool.

---

### User Story 2 - Point and synthesis routes unchanged (Priority: P1)

As bot owner, a single-id fact still uses `point`; a two-method compare still
uses `synthesis`.

**Acceptance Scenarios**:

1. **Given** `/ask 2607.20124`, **when** routed, **then** `point`.
2. **Given** a compare-HFL-VFL question, **when** routed, **then** `synthesis`.

---

## Requirements

- **FR-001**: Router MUST allow `graph` in addition to `point` and `synthesis`.
- **FR-002**: Graph retrieve MUST start from hybrid hits, then add indexed
  papers that share at least one tag with those seeds, then rank chunks among
  that paper set by the same embedding distance as dense search.
- **FR-003**: No new Python packages. No Leiden, no entity table, no GraphRAG
  Microsoft stack.
- **FR-004**: CRAG refuse still applies: insufficient support => no invented
  corpus summary.
- **FR-005**: Empty tags => graph hop adds no neighbors; hybrid seeds only.
  MUST NOT invent a second parser.

## Success Criteria

- **SC-001**: Theme `/ask` announces `graph`.
- **SC-002**: `requirements.txt` unchanged.

## Assumptions

- Many indexed papers have `tags` from enrichment. Untagged seeds isolate the
  hop.
- Community detection is a later spec after library approval.

## Out of Scope

- Entity graphs, Leiden, community summaries, MCP, ACL, Ragas.
