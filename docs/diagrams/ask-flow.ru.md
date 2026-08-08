---
type: Diagram
title: Поток ask — роутинг, hybrid retrieval, синтез
description: /ask, роутинг point vs synthesis, обоснованная генерация и откат к сырым сниппетам.
tags: [diagram, flow, ask, retrieval, synthesis]
lang: ru
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

# Поток ask — роутинг, hybrid retrieval, синтез

🇬🇧 [English version](ask-flow.md)

`/ask` от вопроса до цитируемого ответа. Проза в [../retrieval.ru.md](../retrieval.ru.md).

```mermaid
flowchart TD
    Q["/ask question"] --> R{"route_question<br/>regex-эвристика"}
    R -->|point| HS["hybrid_search(q, 5)"]
    R -->|synthesis| DC["decompose → 2-4 подвопроса<br/>(Gemini JSON / эвристика)"]

    HS --> E{"есть хиты?"}
    E -->|нет| NR["'No relevant chunks found'"]
    E -->|да| GA["generate_answer<br/>Gemini · обязательный [arxiv_id]"]

    DC --> PS["hybrid_search по каждому подвопросу"]
    PS --> GR["группировка по статье (≤ 6)"]
    GR --> MP["map: заметка на статью (Gemini)"]
    MP --> RD["reduce: кросс-статейный цитируемый ответ (Gemini)"]

    GA --> OUT["ответ + дедуплицированный блок Sources"]
    RD --> OUT
    GA -. "ошибка LLM, но хиты есть" .-> SNIP["откат: сырые сниппеты"]
    RD -. "ошибка reduce" .-> GA
```

- **Ready-only**: каждый `hybrid_search` фильтрует `ingest_status = 'indexed'`.
- **Dense + full-text** сливаются через RRF внутри `hybrid_search`; только dense-ветке нужен
  эмбеддинг запроса от Gemini.
- **Sources** дедуплицируются по `arxiv_id` и рендерятся как `arxiv.org/abs/{id}` под ответом.
