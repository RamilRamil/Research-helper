# Feature Specification: Corrective Retrieval and Groundedness

**Feature Branch**: `004-crag-self-rag`  
**Created**: 2026-09-09  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Weak retrieval is not sent to a confident answer (Priority: P1)

As bot owner, if indexed chunks do not actually support my `/ask` question, the
bot refuses instead of answering from noise.

**Why this priority**: hybrid+rerank can still return off-topic scientific
chunks for everyday questions.

**Independent Test**: Ask a question the library cannot answer. Bot does not
produce a cited research-style answer.

**Acceptance Scenarios**:

1. **Given** retrieval returns chunks, **when** a relevance check marks them
   insufficient, **then** no final answer is generated from those chunks.
2. **Given** a second retrieve after one query rewrite still fails the check,
   **then** the user is told the library cannot support the question.

---

### User Story 2 - One rewrite then retrieve again (Priority: P1)

As bot owner, a poorly worded research question gets one reformulation and a
second retrieve before refuse.

**Why this priority**: CRAG without rewrite only refuses; one rewrite recovers
paraphrases without a web pipeline.

**Acceptance Scenarios**:

1. **Given** the first pool fails the relevance check, **when** a rewrite is
   produced, **then** retrieval runs once more with that rewrite.
2. **Given** rewrite or second retrieve fails with an API error, **when** `/ask`
   ends, **then** the user sees an error, not an unranked answer.

---

### User Story 3 - Ungrounded generated text is not shown (Priority: P1)

As bot owner, if the model writes claims not supported by the ranked chunks,
that text is not delivered as the answer.

**Why this priority**: Self-RAG groundedness after generation.

**Acceptance Scenarios**:

1. **Given** a generated draft, **when** a groundedness check fails, **then**
   the user is told the draft was not grounded; the draft is not sent.
2. **Given** the check passes, **when** `/ask` succeeds, **then** Sources still
   come from the ranked hits used for generation.

---

### User Story 4 - Synthesis uses the same gates (Priority: P2)

As bot owner, comparison questions also refuse when the merged pool fails
relevance.

**Acceptance Scenarios**:

1. **Given** synthesis routing and a low-relevance merged pool after one
   rewrite attempt, **then** map/reduce does not run.

---

## Requirements

- **FR-001**: After ranked retrieval, system MUST classify support as
  sufficient or insufficient for the user question.
- **FR-002**: On insufficient, system MUST rewrite the question at most once
  and retrieve again, then classify again.
- **FR-003**: If still insufficient, system MUST NOT call answer generation
  on that pool.
- **FR-004**: After a generated point answer, system MUST check groundedness
  against the ranked chunks. Fail => do not send the draft.
- **FR-005**: No web search, no new packages. Use existing Gemini generate.
- **FR-006**: Do not silently skip CRAG on 503; model chain in `llm.py` already
  applies. If all models fail, surface the error.
- **FR-007**: `/list` and ingest unchanged.

## Success Criteria

- **SC-001**: A non-library question yields a refuse, not a paper-flavored
  hallucination.
- **SC-002**: A known in-library fact question still answers with Sources.
- **SC-003**: Owner can paste one refuse command and one success command.

## Assumptions

- One extra grade call (and maybe rewrite + second retrieve + groundedness)
  per `/ask` is acceptable quota cost for this pillar.
- Web fallback stays out until a later spec.

## Out of Scope

- GraphRAG, planner, MCP, ACL, eval framework Ragas.
- Changing chunking or hybrid fusion.
