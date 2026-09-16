# Feature Specification: Leiden Communities on the Paper Graph

**Feature Branch**: `011-leiden-communities`  
**Created**: 2026-09-11  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Library themes come from communities, not one FL paper (Priority: P1)

As bot owner, a graph `/ask` about themes uses paper communities (Leiden), not
only tag/category neighbor dump.

**Why this priority**: category hop is `cs.LG` soup; true GraphRAG needs
clusters and cluster writeups.

**Independent Test**: After community build, graph `/ask` about a theme cites
more than one paper when several indexed papers share a community, or states
the community is a single paper.

**Acceptance Scenarios**:

1. **Given** indexed papers with categories or tags, **when** owner builds
   communities, **then** each indexed paper has one community id.
2. **Given** a community with several papers, **when** graph retrieve runs,
   **then** chunks can come from those papers, not only the hybrid seed.
3. **Given** communities exist, **when** graph answers, **then** it may use a
   stored community summary plus retrieved chunks; citations stay arXiv ids.

---

## Requirements

- **FR-001**: MUST compute Leiden communities on the undirected paper graph
  (edge if shared tag or shared category).
- **FR-002**: MUST persist community assignment and a short summary per
  community.
- **FR-003**: Graph retrieve MUST expand seeds to the same community.
- **FR-004**: Owner MUST trigger rebuild explicitly (not on every `/ask`).
- **FR-005**: Approved new libraries: `igraph` and `leidenalg` only for this
  feature.

## Success Criteria

- **SC-001**: Community rebuild finishes on the current indexed set without
  dropping papers from retrieval.
- **SC-002**: One graph `/ask` lists Sources from more than one arXiv id when
  the seed community has more than one indexed paper.

## Assumptions

- Graph is papers, not token entities.
- Summaries are extractive from stored paper `summary_en` / titles (no generate on rebuild).

## Out of Scope

- Entity-level GraphRAG, MCP, Ragas, LaTeX.
