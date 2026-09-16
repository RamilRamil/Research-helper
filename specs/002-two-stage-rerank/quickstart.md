# Quickstart: Two-Stage Rerank

## Point path

1. `/ask` a fact that exists in an indexed paper.
2. Confirm thinking line still shows `point`.
3. Answer cites `[arxiv_id]` from Sources.
4. Optional: log pool size vs context size (20 vs 5) in a debug session only
   if the owner later allows logging; do not add debug prints in production
   code.

## Ranker failure

1. Temporarily break API key or model name in a local run, or wait for 429.
2. `/ask` must show an error, not a full answer from raw hybrid hits.

## Synthesis path

1. `/ask` a compare/survey question that routes to `synthesis`.
2. Sources come from reranked merged hits.

## Quota

If Gemini generate is exhausted, record the visible error. Do not "fix" by
skipping rerank.
