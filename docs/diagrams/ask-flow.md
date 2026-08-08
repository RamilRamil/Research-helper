---
type: Diagram
title: Ask flow — routing, hybrid retrieval, synthesis
description: /ask routed into point vs synthesis, grounded generation, and the raw-snippet fallback.
tags: [diagram, flow, ask, retrieval, synthesis]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/bot/main.py
    title: cmd_ask
  - resource: app/rag/router.py
    title: route_question
  - resource: app/rag/synthesis.py
    title: synthesize_answer
---

# Ask flow — routing, hybrid retrieval, synthesis

🇷🇺 [Русская версия](ask-flow.ru.md)

`/ask` from question to cited answer. Prose in [../retrieval.md](../retrieval.md).

```mermaid
flowchart TD
    Q["/ask question"] --> R{"route_question<br/>regex heuristic"}
    R -->|point| HS["hybrid_search(q, 5)"]
    R -->|synthesis| DC["decompose → 2-4 subs<br/>(Gemini JSON / heuristic)"]

    HS --> E{"hits?"}
    E -->|no| NR["'No relevant chunks found'"]
    E -->|yes| GA["generate_answer<br/>Gemini · mandatory [arxiv_id]"]

    DC --> PS["hybrid_search per sub-question"]
    PS --> GR["group by paper (≤ 6)"]
    GR --> MP["map: per-paper note (Gemini)"]
    MP --> RD["reduce: cross-paper cited answer (Gemini)"]

    GA --> OUT["answer + deduped Sources block"]
    RD --> OUT
    GA -. "LLM error but hits exist" .-> SNIP["fallback: raw retrieved snippets"]
    RD -. "reduce error" .-> GA
```

- **Ready-only**: every `hybrid_search` filters `ingest_status = 'indexed'`.
- **Dense + full-text** are fused by RRF inside `hybrid_search`; only the dense leg needs a Gemini
  query embedding.
- **Sources** are deduped by `arxiv_id` and rendered as `arxiv.org/abs/{id}` under the answer.
