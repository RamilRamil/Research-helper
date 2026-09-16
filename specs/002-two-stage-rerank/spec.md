# Feature Specification: Two-Stage Retrieval Rerank

**Feature Branch**: `002-two-stage-rerank`  
**Created**: 2026-09-09  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Point questions get a tight cited context (Priority: P1)

As bot owner, I ask a factual question with `/ask` and the answer is built from a
small set of highly relevant passages, not from a noisy hybrid top list.

**Why this priority**: hybrid RRF already recalls mixed chunks; generation then
wastes attention on mid-list noise (lost-in-the-middle).

**Independent Test**: For one known indexed paper fact, retrieve a wide eligible
pool then a short final list. The supporting chunk of that fact is in the final
list; at least one clearly off-topic pool chunk is not.

**Acceptance Scenarios**:

1. **Given** indexed chunks exist, **when** I ask a point question, **then**
   generation context size is the configured final K (small), not the full pool.
2. **Given** hybrid retrieval returns a mixed pool, **when** rerank runs, **then**
   order of the final list can differ from raw RRF order.
3. **Given** hybrid retrieval returns nothing eligible, **when** I ask, **then**
   I am told no chunks were found and no answer is invented.

---

### User Story 2 - Citations stay inside reranked evidence (Priority: P1)

As bot owner, `/ask` citations refer only to papers/chunks that survived rerank.

**Why this priority**: citing a dropped noisy hit is a groundedness bug.

**Independent Test**: Capture the final context list and the answer. Every
`[arxiv_id]` in the answer exists in that list.

**Acceptance Scenarios**:

1. **Given** a successful point `/ask`, **when** the answer contains `[arxiv_id]`,
   **then** that id appears in the reranked context sent to generation.
2. **Given** rerank kept K chunks, **when** Sources are listed, **then** they are
   derived from those chunks (or a subset), not from discarded pool rows.

---

### User Story 3 - Rerank failure is visible (Priority: P1)

As bot owner, if the second-stage ranker cannot run, I see a failure. The bot
MUST NOT silently answer from the unranked pool.

**Why this priority**: a hidden fallback hides quality regressions and burns
quota on a path the owner did not choose.

**Independent Test**: Force second-stage failure (invalid model response or API
error). `/ask` reports failure; no grounded paragraph is produced from the raw
pool.

**Acceptance Scenarios**:

1. **Given** hybrid found chunks, **when** rerank fails, **then** the user sees
   an error and no completed answer from unranked hits.
2. **Given** rerank returns no usable ranked ids, **when** `/ask` continues,
   **then** it MUST NOT call generation on the raw pool.

---

### User Story 4 - Synthesis also uses reranked passages (Priority: P2)

As bot owner, comparison `/ask` questions still gather a wide pool per
subquestion but map/reduce sees reranked passages, not only raw RRF tops.

**Why this priority**: synthesis already multiplies retrieval; without rerank it
maps noise.

**Independent Test**: A comparison question produces per-paper notes whose
source chunks are a reranked subset of the merged hybrid pool.

**Acceptance Scenarios**:

1. **Given** a synthesis-routed question and a non-empty merged pool, **when**
   map/reduce runs, **then** mapped excerpts come from reranked hits.
2. **Given** rerank fails on the synthesis path, **when** `/ask` ends, **then**
   the user sees failure; map/reduce MUST NOT proceed on the unranked merge.

---

## Requirements

- **FR-001**: Point `/ask` MUST retrieve an eligible hybrid pool larger than the
  generation context, then keep only the top K chunks after second-stage ranking
  for generation. Default K is 5. Default pool size is 20.
- **FR-002**: Second-stage ranking MUST consider the user question and chunk
  text (not RRF score alone).
- **FR-003**: `/ask` Sources MUST be built from post-rerank hits only.
- **FR-004**: If second-stage ranking fails or yields an empty usable list while
  the pool was non-empty, the system MUST fail the request visibly and MUST NOT
  generate an answer from the unranked pool.
- **FR-005**: Ready-only retrieval rules from feature 001 MUST remain (only
  `indexed` papers, chunks with embeddings).
- **FR-006**: Synthesis-routed `/ask` MUST apply the same second-stage ranking
  to the merged retrieval pool before map/reduce.
- **FR-007**: This feature MUST NOT add a new paid ranking API or a new Python
  package. Ranking MUST use the already configured Gemini generate client.
- **FR-008**: Existing commands besides `/ask` context assembly (`/search`,
  `/list`, ingest) MUST keep current retrieval behavior unless they share the
  `/ask` helper.

## Success Criteria

- **SC-001**: For a documented point question, generation receives exactly K
  chunks when the pool has at least K hits (K=5 unless noted).
- **SC-002**: On that question, at least one irrelevant pool chunk present in
  the wide list is absent from the final K.
- **SC-003**: 100% of `[arxiv_id]` citations in a sampled successful answer
  appear in the reranked context.
- **SC-004**: Injected rerank failure yields zero completed answers from the
  unranked pool in the test run.
- **SC-005**: One synthesis-routed question uses reranked hits for map inputs.

## Key Entities

- **Retrieval pool**: hybrid (dense + full-text + RRF) candidate chunks, size
  up to the configured pool limit, ready-only.
- **Ranked context**: ordered subset of the pool, length K, passed to
  generation or synthesis map.
- **Ranking decision**: question-conditioned ordering (and optional drops) of
  pool chunk ids.

## Assumptions

- Feature 001 ingest/retrieval eligibility is already in production.
- Hybrid search with RRF is the first stage; this feature does not replace it.
- Default pool 20 and K 5 balance recall vs Gemini free-tier generate quota
  (one extra generate call per `/ask` point path).
- No Cohere, no local cross-encoder, no new Docker services.
- `/list` stays hybrid-only (no rerank) to avoid doubling quota on browse.

## Out of Scope

- GraphRAG, CRAG/Self-RAG, agent planner (later specs).
- Changing chunking or ingest.
- Replacing Postgres FTS with BM25 engines.
- Automatic retries or degraded unranked `/ask` when Gemini is 429/503.
- MCP, ACL.
