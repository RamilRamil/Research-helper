# Tasks: Two-Stage Retrieval Rerank

**Input**: `specs/002-two-stage-rerank/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `contracts/rerank.md`

## Dependencies

```text
rerank_hits -> retrieve_for_ask -> cmd_ask point
rerank_hits -> synthesize_answer merge
```

## Phase 1: Ranker

- [x] T001 Add `rerank_hits` in `app/rag/rerank.py` (Gemini JSON `chunk_ids`, keep N, fail closed).
- [x] T002 Add `retrieve_for_ask` in `app/rag/rerank.py` (hybrid pool 20 then keep 5).

## Phase 2: User Story 1-3 point `/ask`

- [x] T003 [US1] Wire `cmd_ask` point path to `retrieve_for_ask` in `app/bot/main.py`.
- [x] T004 [US3] Ensure ranker exceptions reach the user without `generate_answer` on the unranked pool.

## Phase 3: User Story 4 synthesis

- [x] T005 [US4] Rerank merged unique hits in `app/rag/synthesis.py` before map; propagate ranker errors.

## Phase 4: Polish

- [x] T006 Record a live `/ask` point or documented 429 fail-closed result in `specs/002-two-stage-rerank/implementation-notes.md`.
- [x] T007 Update `specs/README.md` and `.specify/feature.json` status; do not edit ingest 001 behavior.
