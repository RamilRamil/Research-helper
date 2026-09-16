# Contract: retrieve_for_ask / rerank_hits

## `rerank_hits(question, hits, keep=5) -> list[dict]`

- `hits` non-empty; each item MUST have `chunk_id`.
- Returns at most `keep` items, subset of input, question-conditioned order.
- If the model omits every id (none relevant), return empty list. MUST NOT
  return the input list unchanged.
- Raises on empty input, missing `chunk_id`, empty/invalid model JSON.

## `retrieve_for_ask(question) -> list[dict]`

- First stage: existing `hybrid_search` with pool 20.
- Empty pool => empty list, no ranker call.
- Non-empty pool => `rerank_hits(..., keep=5)`.

## `/ask` point

MUST call `retrieve_for_ask`. MUST NOT call `generate_answer` on unranked pool
after ranker failure.

## Synthesis `synthesize_answer`

MUST rerank the merged unique hybrid hits before map. Ranker failure MUST
propagate to `/ask`.
