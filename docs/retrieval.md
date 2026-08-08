---
type: Reference
title: Retrieval & answering — hybrid search, routing, grounded answers
description: Dense halfvec + Postgres full-text fused with RRF, ready-only filtering, /ask routing (point vs synthesis), and cited answers.
tags: [retrieval, hybrid-search, rrf, rag, answering, synthesis]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/db/search.py
    title: search_chunks / full_text_search / hybrid_search / _rrf_fuse
  - resource: app/rag/router.py
    title: route_question
  - resource: app/rag/answer.py
    title: generate_answer
  - resource: app/rag/synthesis.py
    title: synthesize_answer
---

# Retrieval & answering

🇷🇺 [Русская версия](retrieval.ru.md)

Retrieval combines a **dense** vector search with **Postgres full-text** and fuses them, then
`/ask` routes the question to either a direct answer or a multi-paper synthesis. Every retrieval
path is **ready-only** — it filters `ingest_status = 'indexed'`, so incomplete papers never reach
an answer. The `/ask` flow diagram is in [diagrams/ask-flow.md](diagrams/ask-flow.md).

## The two retrieval legs

- **Dense** (`search_chunks`) — embeds the query with Gemini (`task_type=RETRIEVAL_QUERY`) and
  orders chunks by cosine distance `embedding <=> $vec::halfvec(3072)`, `WHERE embedding IS NOT NULL
  AND p.ingest_status = 'indexed'`.
- **Full-text** (`full_text_search`) — `plainto_tsquery('english', q)` against the generated
  `text_search` tsvector, ranked by `ts_rank`, same ready-only filter. Catches exact terms /
  model names that dense similarity blurs.

## Fusion: `hybrid_search`

`hybrid_search(query, limit=5, fetch_k=20)` takes the top `fetch_k` from each leg and merges them
with **Reciprocal Rank Fusion** (`_rrf_fuse`, `k=60`): each chunk scores `Σ 1/(k + rank)` across
the lists it appears in, best-known fields are merged, and a chunk found by both legs is tagged
`source = "hybrid"`. The top `limit` chunks come back with `arxiv_id`, `title`, `section`, `text`,
a 200-char `snippet`, and the fusion score. This is the single retrieval entry point used by
`/ask`, `/list`, and synthesis.

## `/ask` routing: point vs synthesis

`route_question` ([router.py](../app/rag/router.py)) is a **regex heuristic, not an LLM call** —
EN/RU patterns like *compare*, *difference*, *vs*, *survey*, *сравни*, *чем отлича*, *все статьи*
route to `synthesis`; everything else is `point`.

**point** → `hybrid_search(q, 5)` → `generate_answer` ([answer.py](../app/rag/answer.py)): a
Gemini call (`gemini-flash-latest`, temperature 0.2, 3 retries) that must cite every claim as
`[arxiv_id]`, may write `[id1][id2]`, must say when context is insufficient rather than invent, and
answers in the question's language.

**synthesis** → `synthesize_answer` ([synthesis.py](../app/rag/synthesis.py)), a map-reduce:

1. **Decompose** — one Gemini JSON call splits the question into 2–4 sub-questions; on failure it
   falls back to a fixed heuristic set.
2. **Retrieve per sub** — `hybrid_search` for each sub-question, results pooled.
3. **Group** — dedupe chunks and group by `arxiv_id` (up to 6 papers).
4. **Map** — one Gemini call per paper summarizes what *that* paper says (≤4 excerpts), cited.
5. **Reduce** — one Gemini call writes the cross-paper comparison from the per-paper notes; if it
   fails, it falls back to `generate_answer` over the pooled hits.

Both modes return `(answer, hits)`; the bot posts the answer, then a deduped **Sources** block
(`arxiv_id`, title, `arxiv.org/abs/{id}`).

## `/list` and the snippet fallback

`/list <topic>` runs `hybrid_search(topic, 15)`, dedupes by `arxiv_id`, and shows the top 10 as a
library listing (no generation). In `/ask`, if answer generation raises but hits exist, the bot
degrades gracefully to posting the **raw retrieved snippets** instead of an error.

## Current limits

- **Routing is heuristic.** No LLM classifies intent; a comparison phrased without a trigger word
  goes down the `point` path.
- **Synthesis sources are capped** (≤6 papers mapped; 2 chunks/paper kept for the Sources list).
- **Dense still needs Gemini** for the query embedding — the full-text leg is the only part that
  works without it.
