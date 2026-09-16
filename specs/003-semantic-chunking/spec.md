# Feature Specification: Semantic Adaptive Chunking

**Feature Branch**: `003-semantic-chunking`  
**Created**: 2026-09-09  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - New ingest keeps ideas in one fragment (Priority: P1)

As bot owner, when a new paper is indexed, long sections are split at natural
breaks (paragraph or sentence), not in the middle of a sentence.

**Why this priority**: character windows break coreference and hurt retrieval
recall for `/ask`.

**Independent Test**: Take one long section of extracted PDF text. After
chunking, no chunk (except possibly a single token longer than the size cap)
ends mid-word; sentence-final punctuation is preferred at chunk ends.

**Acceptance Scenarios**:

1. **Given** a section shorter than the size cap, **when** chunking runs,
   **then** it remains one chunk with its section label.
2. **Given** a section longer than the cap, **when** chunking runs, **then**
   each part is at most the cap (unless one unsplittable unit is longer) and
   consecutive parts may overlap on a trailing coherent unit, not a raw
   character slice through a word.
3. **Given** section headings are detected, **when** chunks are stored,
   **then** each chunk still has that section label.

---

### User Story 2 - Already indexed papers stay untouched (Priority: P1)

As bot owner, changing the chunker MUST NOT rewrite `indexed` papers during
normal `/search`.

**Why this priority**: feature 001 made `indexed` immutable for normal search.

**Independent Test**: After deploying the new chunker, repeat `/search` on a
topic with indexed hits. Those papers keep the same chunk count.

**Acceptance Scenarios**:

1. **Given** a paper is `indexed`, **when** I run normal search, **then** its
   chunks are not deleted or re-embedded.
2. **Given** a paper is `pending`, `text_ok`, or `failed`, **when** I `/reindex`
   it, **then** the new chunker is used for that paper only.

---

### User Story 3 - Retrieval still ready-only (Priority: P2)

As bot owner, `/ask` still sees only `indexed` embeddings. Mixed old/new chunk
shapes in the library are allowed.

**Why this priority**: corpus will contain pre-003 windows and post-003 packs
until an explicit future reindex feature exists.

**Independent Test**: `/ask` after ingesting one new paper still returns only
`indexed` sources.

**Acceptance Scenarios**:

1. **Given** mixed chunk styles in the DB, **when** I `/ask`, **then** only
   indexed papers appear in Sources.
2. **Given** no staged reindex feature, **when** this feature ships, **then**
   documentation states old papers keep old chunks.

---

## Requirements

- **FR-001**: Chunking MUST still split by detected PDF section first, then
  subdivide long sections.
- **FR-002**: Subdivision MUST prefer paragraph and sentence boundaries over a
  fixed character cut through words.
- **FR-003**: A size cap MUST remain so embeddings stay bounded.
- **FR-004**: Normal `/search` MUST NOT rechunk `indexed` papers.
- **FR-005**: `/reindex` of incomplete papers MUST use the new chunker.
- **FR-006**: No new Python package and no extra Gemini calls per sentence
  (no perplexity MCPD in this feature).
- **FR-007**: Section labels MUST still be stored on each chunk.

## Success Criteria

- **SC-001**: On a fixture section longer than the cap, at least 80% of
  produced chunks end on whitespace or sentence punctuation, not mid-word.
- **SC-002**: Repeat search does not change chunk counts of already indexed
  papers.
- **SC-003**: One newly ingested or reindexed incomplete paper stores chunks
  with section labels and embeddings and reaches `indexed` or `failed`.

## Key Entities

- **Section**: labeled span of paper text from heading detection.
- **Chunk**: searchable unit with text, section, hash, embedding.
- **Size cap**: maximum preferred character length per chunk.

## Assumptions

- PDF section regex from 001 evaluation is retained (retain-PDF decision).
- MCPD / LLM-perplexity chunking is a later spec (quota and new method).
- Staged reindex of `indexed` papers is out of this feature.
- English-centric sentence split is acceptable (arxiv main text).

## Out of Scope

- LaTeX-first ingest, GraphRAG, CRAG, citation-prompt `[arxiv_id]` tweak.
- Rewriting the existing indexed library.
- New embedding model.
