# Feature Specification: Cite arXiv IDs and Graph Neighbors

**Feature Branch**: `008-cite-and-neighbors`  
**Created**: 2026-09-10  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Answers cite arXiv ids only (Priority: P1)

As bot owner, in-body citations look like `[2607.20124]`, not `[1]` or `[2]`.

**Why this priority**: numbered context labels taught the model the wrong cite
form.

**Independent Test**: `/ask` a known paper fact. The answer body uses
bracketed arXiv ids that appear in Sources. No standalone `[1]` cite tokens.

**Acceptance Scenarios**:

1. **Given** ranked chunks with arXiv ids, **when** generation runs, **then**
   context lines are labeled with those ids, not a separate 1-based index.
2. **Given** a successful `/ask`, **when** I read the answer, **then** citation
   tokens match the Sources ids.

---

### User Story 2 - Graph hop works without tags (Priority: P1)

As bot owner, a `graph` `/ask` can still reach other indexed papers when
`tags` are empty, using arXiv categories already stored on the paper.

**Why this priority**: FL theme ask stayed on one id because tag overlap was
empty.

**Acceptance Scenarios**:

1. **Given** seed papers with empty tags but non-empty categories, **when**
   neighbor lookup runs, **then** other indexed papers sharing a category can
   be included (up to the existing neighbor cap).
2. **Given** tag overlap exists, **when** neighbor lookup runs, **then** tags
   are used first and categories are not required.

---

## Requirements

- **FR-001**: Generation context MUST label each chunk with its arXiv id as
  the citation key. MUST NOT prefix a competing numeric cite index.
- **FR-002**: The generate prompt MUST forbid `[1]`-style cites.
- **FR-003**: Graph neighbor lookup MUST use tag overlap when present; if that
  set is empty, MUST use category overlap among indexed papers.
- **FR-004**: No new packages. No bulk re-enrich of the whole library in this
  feature.
- **FR-005**: Neighbor cap stays bounded (same order as current graph hop).

## Success Criteria

- **SC-001**: One `/ask` answer uses `[arxiv_id]` in the body, not `[1]`.
- **SC-002**: One `graph` `/ask` can list more than one Source id when other
  indexed papers share a category with the seed.

## Assumptions

- `categories` is populated at ingest from arXiv. Broad categories may link
  loosely; cap prevents dumping the whole corpus.
- Author-overlap hop is out of this slice (JSONB shape varies).

## Out of Scope

- Staged reindex of old chunks, Leiden, Ragas, MCP, ACL.
