# Feature Specification: Stabilize RAG Ingest

**Feature Branch**: `001-stabilize-rag-ingest`  
**Created**: 2026-07-23  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Avoid duplicate processing (Priority: P1)

As bot owner, I search an already processed topic and receive paper results without
waiting for the same PDF files to download and index again.

**Why this priority**: repeated processing wastes model quota, makes `/search` slow,
and can overwrite a working index after a transient failure.

**Independent Test**: Search twice for same topic. On second search, already
successfully indexed papers are reported as skipped; their PDF files, chunks, and
embeddings are not recreated.

**Acceptance Scenarios**:

1. **Given** a paper has completed indexing, **when** it appears in a later search,
   **then** system does not process it again and records it as already indexed.
2. **Given** a paper is new, **when** it appears in search results, **then** system
   stores its metadata, PDF, extracted content, and index once.
3. **Given** a paper is already `indexed`, **when** it appears in a later search,
   **then** normal search does not modify its stored representation.

---

### User Story 2 - Observe reliable ingest result (Priority: P1)

As bot owner, I can determine whether every discovered paper is awaiting work,
processed successfully, or failed, and can see why a failed paper did not finish.

**Why this priority**: state drives safe retry and prevents silently searching an
incomplete source.

**Independent Test**: Cause a processing error for one paper and complete another.
Persisted records show distinct terminal states; failed record has safe diagnostic
message and successful record is searchable.

**Acceptance Scenarios**:

1. **Given** a paper is discovered, **when** processing has not started, **then**
   its state is `pending`.
2. **Given** text extraction succeeds, **when** indexing remains to be completed,
   **then** its state is `text_ok`.
3. **Given** all required index data is stored, **when** ingest ends, **then** its
   state is `indexed`.
4. **Given** any ingest stage fails, **when** operation ends, **then** its state is
   `failed` and diagnostic detail is saved without exposing credentials.
5. **Given** a legacy paper exists before lifecycle rollout, **when** rollout runs,
   **then** it is explicitly classified as `indexed` or `failed` before ready-only
   retrieval is enabled.

---

### User Story 3 - Recover an incomplete paper (Priority: P1)

As bot owner, I can explicitly resume one incomplete paper without automatic repeated
processing during unrelated topic searches.

**Why this priority**: temporary download, extraction, or embedding failures otherwise
leave papers permanently unavailable after normal search begins skipping existing rows.

**Independent Test**: Run `/reindex <arxiv_id>` for one `failed` and one `text_ok`
paper. Both return to a completed searchable state or a newly recorded failure.

**Acceptance Scenarios**:

1. **Given** a paper is `pending`, `text_ok`, or `failed`, **when** owner runs
   `/reindex <arxiv_id>`, **then** system explicitly restarts its incomplete ingest.
2. **Given** a paper is `indexed`, **when** owner runs `/reindex <arxiv_id>`, **then**
   system rejects the request without modifying its working index.
3. **Given** reindex fails, **when** PDF was previously stored, **then** PDF remains
   available and state becomes `failed` with safe diagnostic detail.
4. **Given** ingest or reindex for one arXiv ID is already running, **when** a second
   `/search` or `/reindex` targets the same ID, **then** system rejects concurrent work
   without corrupting chunks or embeddings.

---

### User Story 4 - Search only ready sources (Priority: P2)

As bot owner, I receive retrieval results only from fully indexed papers and do not
receive passages from incomplete or failed processing attempts.

**Why this priority**: source quality and citation reliability depend on the returned
paper being complete.

**Independent Test**: Seed ready and non-ready records with chunks. Search returns
only passages belonging to `indexed` papers.

**Acceptance Scenarios**:

1. **Given** a paper is `pending`, `text_ok`, or `failed`, **when** user asks a
   question, **then** none of its chunks appear in results.
2. **Given** a paper is `indexed`, **when** it has relevant chunks, **then** its
   chunks remain eligible for retrieval.

---

### User Story 5 - Keep retrieval responsive as library grows (Priority: P2)

As bot owner, I can query an expanding paper library without retrieval becoming
unreasonably slow due to scanning every stored chunk.

**Why this priority**: vector retrieval is currently unindexed and will degrade with
library growth.

**Independent Test**: On a representative indexed corpus, query plan demonstrates an
approximate-nearest-neighbor index is eligible for retrieval; query latency is
recorded as a baseline for later features.

---

### User Story 6 - Decide whether PDF sections are trustworthy (Priority: P3)

As bot owner, I have measured evidence of whether extracted PDF sections are reliable
enough for section-aware retrieval before adopting a more complex source parser.

**Why this priority**: section labels are already stored but may be wrong when PDF
layout breaks headings.

**Independent Test**: Review a sample of at least five papers across categories.
Record section-label coverage, false detections, missed headings, and a decision to
retain PDF extraction or start a separate LaTeX-first feature.

## Requirements

- **FR-001**: System MUST treat a paper in `indexed` state as reusable during normal
  search ingest and MUST NOT recreate its stored PDF, chunks, or embeddings.
- **FR-002**: System MUST retain a successfully stored PDF when later indexing work
  fails.
- **FR-003**: System MUST record each paper's state as `pending`, `text_ok`,
  `indexed`, or `failed`.
- **FR-004**: System MUST record a diagnostic message for a failed ingest attempt.
- **FR-005**: System MUST transition a paper to `indexed` only after all required
  searchable chunks have embeddings.
- **FR-006**: Before ready-only retrieval is enabled, system MUST classify each legacy
  paper explicitly as `indexed` or `failed` without deleting its PDF.
- **FR-007**: System MUST provide `/reindex <arxiv_id>` to resume only `pending`,
  `text_ok`, or `failed` papers. It MUST reject an `indexed` paper without mutation.
- **FR-008**: System MUST prevent concurrent ingest or reindex of the same arXiv ID.
  A second concurrent attempt MUST be rejected without mutating stored data.
- **FR-009**: System MUST exclude every paper not in `indexed` state from retrieval.
- **FR-010**: System MUST provide an index path suitable for nearest-neighbor
  retrieval over existing paper chunks.
- **FR-011**: System MUST preserve existing user-visible commands and PDF retention.
- **FR-012**: Project MUST produce a section-label evaluation report using at least
  five stored research papers before changing source-extraction strategy.

## Success Criteria

- **SC-001**: A repeat search over ten already indexed papers causes zero new PDF
  downloads and zero new embedding requests.
- **SC-002**: 100% of completed ingest attempts end in exactly one observable
  terminal state: `indexed` or `failed`.
- **SC-003**: Every legacy paper is classified before retrieval filtering; for current
  corpus, exactly two legacy records have an auditable before/after classification.
- **SC-004**: `/reindex` successfully resumes one `failed` and one `text_ok` paper,
  or records a new safe `failed` result without deleting either PDF.
- **SC-005**: Concurrent ingest/reindex of one arXiv ID is rejected; stored chunk count
  and embeddings remain unchanged for the rejected attempt.
- **SC-006**: Retrieval returns zero chunks from incomplete or failed papers in
  acceptance scenarios.
- **SC-007**: Query-plan review confirms indexed nearest-neighbor retrieval for
  representative library data.
- **SC-008**: Section evaluation covers at least five papers and results in an
  explicit retain-PDF or propose-LaTeX decision.

## Key Entities

- **Paper**: one arXiv work with metadata, local PDF location, processing state, and
  failure detail.
- **Chunk**: searchable passage belonging to a paper, with text, section label, hash,
  and embedding.
- **Ingest attempt**: processing of one paper from discovery through searchable index.
- **Section evaluation record**: manual assessment of labels extracted from a sampled
  paper.

## Assumptions

- Existing local PDF storage remains authoritative for the personal library.
- `/reindex` is owner-only through existing Telegram whitelist.
- Exactly two legacy `papers` records exist at feature-planning time; owner may add
  more papers before section evaluation so the five-paper sample is reachable.
- `indexed` means searchable after embeddings succeed; summaries and tags are later
  enrichment and are not required for readiness.
- Manual build follows `docs/plan/05-build-roadmap.md` Phase 3.5; this Spec Kit feature
  is the detailed execution plan for that phase.
- No new external service or library is needed for this feature.

## Out of Scope

- Hybrid dense and full-text retrieval (roadmap Phase 5).
- Generated answers, citations, summaries, tags, and question routing
  (roadmap Phases 4, 6, 7).
- LangGraph orchestration (roadmap Phase 8).
- LaTeX source download, visual/diagram retrieval, PageIndex, or T-Search.
- Reindexing an already `indexed` paper, index versioning, and automatic retries.
