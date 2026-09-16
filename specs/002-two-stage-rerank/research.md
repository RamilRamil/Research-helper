# Research: Two-Stage Rerank

## Decision: Gemini listwise, no new library

Options: Cohere Rerank, local cross-encoder, Gemini listwise on existing client.

Chosen: Gemini listwise JSON of chunk ids. Constitution forbids new packages
without approval. Free-tier generate quota is already the bottleneck; a second
vendor does not help.

Rejected: silent skip of rerank on 429 (forbidden fallback).

## Pool 20 / K 5

Classic "top 50 then top 3" costs long prompts. 20/5 fits Telegram latency and
quota. RRF `fetch_k` already 20 in `hybrid_search`.

## Synthesis

Rerank once on the merged unique pool vs the original question, keep 12, then
existing map cap 6 papers. Avoids N rerank calls per subquestion.
