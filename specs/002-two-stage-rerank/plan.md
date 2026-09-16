# Implementation Plan: Two-Stage Retrieval Rerank

## Technical Context

| Area | Current state | Planned change |
|------|---------------|----------------|
| First stage | `hybrid_search` RRF, `/ask` point uses `limit=5` | Point `/ask`: pool 20, then K=5 after rerank |
| Ranker | none | `app/rag/rerank.py` listwise Gemini JSON of `chunk_id` order |
| Ask | `cmd_ask` hybrid then `generate_answer` | insert rerank; fail closed |
| Synthesis | `hybrid_search` per subquestion | merge unique hits, rerank vs original question, then map |
| List/search | hybrid / ingest | unchanged |
| Dependencies | google genai already used | no new packages |

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| Spec Kit execution | Pass | this folder |
| One pillar | Pass | two-stage rerank only |
| Ingest integrity | Pass | no ingest/schema change |
| Groundedness | Pass | generate only on ranked hits |
| No duplicate pipelines | Pass | extend hybrid, do not add ES/Qdrant |
| No silent fallback | Pass | rerank fail => visible error |
| Deps gated | Pass | existing Gemini generate |
| Eval | Pass | quickstart records one point + one synthesis question |

## Design

### 1. Pool then rank

`retrieve_for_ask(question) -> list[dict]`:
- `hybrid_search(question, limit=20, fetch_k=20)`
- if empty, return []
- `rerank_hits(question, pool, keep=5)`
- rerank raises on API/parse/empty-usable-id failure

`rerank_hits`: one `generate_content` call. Prompt: question + numbered
`chunk_id` + truncated text (ASCII prompt). Model returns JSON
`{"chunk_ids": ["...", ...]}`. Keep first `keep` ids that exist in the pool,
stable original fields. Duplicate ids skipped.

### 2. Point `/ask`

Replace `hybrid_search(question, 5)` with `retrieve_for_ask`. Sources from
returned hits. If rerank raises, existing error branch with empty hits shows
the error (do not fill hits from pool).

### 3. Synthesis

After merging subquestion hybrid hits (still `per_sub_limit=5` per sub to
limit embed cost), unique by `chunk_id`, call `rerank_hits(question, merged,
keep=12)`. Then existing group/map/reduce on that list. If rerank raises,
propagate; do not `_heuristic` around rerank. Existing decompose heuristic
stays out of this feature (do not add new fallbacks).

### 4. Quota

One extra generate per point `/ask`. Synthesis: one extra generate for
rerank (decompose/map/reduce already exist). Owner already hit free-tier 20/day
on enrich; `/ask` can 429. Fail closed. Do not retry-loop in rerank (unlike
`generate_answer`).

## File-Level Changes

| File | Change |
|------|--------|
| `app/rag/rerank.py` | `rerank_hits`, `retrieve_for_ask` |
| `app/bot/main.py` | point path uses `retrieve_for_ask` |
| `app/rag/synthesis.py` | rerank merged pool before map |
| `specs/002-two-stage-rerank/` | research, contract, quickstart |

## Verification

See `quickstart.md`. Live `/ask` may 429; then record failure-closed behavior.

## Deferred

CRAG, GraphRAG, planner, `/list` rerank, dedicated cross-encoder.
