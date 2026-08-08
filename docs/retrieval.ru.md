---
type: Reference
title: Поиск и ответы — hybrid search, роутинг, обоснованные ответы
description: Dense halfvec + Postgres full-text через RRF, ready-only фильтрация, роутинг /ask (point vs synthesis) и цитируемые ответы.
tags: [retrieval, hybrid-search, rrf, rag, answering, synthesis]
lang: ru
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

# Поиск и ответы

🇬🇧 [English version](retrieval.md)

Retrieval объединяет **dense** векторный поиск с **Postgres full-text** и сливает их, затем
`/ask` роутит вопрос либо в прямой ответ, либо в multi-paper синтез. Каждый путь retrieval
**ready-only** — фильтрует `ingest_status = 'indexed'`, так что незавершённые статьи не попадают в
ответ. Диаграмма потока `/ask` — в [diagrams/ask-flow.md](diagrams/ask-flow.md).

## Две ветки retrieval

- **Dense** (`search_chunks`) — эмбеддит запрос через Gemini (`task_type=RETRIEVAL_QUERY`) и
  упорядочивает чанки по косинусному расстоянию `embedding <=> $vec::halfvec(3072)`, `WHERE
  embedding IS NOT NULL AND p.ingest_status = 'indexed'`.
- **Full-text** (`full_text_search`) — `plainto_tsquery('english', q)` по сгенерированному
  tsvector `text_search`, ранжирование `ts_rank`, тот же ready-only фильтр. Ловит точные термины /
  названия моделей, которые dense-схожесть размывает.

## Слияние: `hybrid_search`

`hybrid_search(query, limit=5, fetch_k=20)` берёт топ `fetch_k` из каждой ветки и сливает их через
**Reciprocal Rank Fusion** (`_rrf_fuse`, `k=60`): каждый чанк получает `Σ 1/(k + rank)` по спискам,
где встретился, известные поля мёржатся, а чанк, найденный обеими ветками, помечается `source =
"hybrid"`. Топ `limit` чанков возвращается с `arxiv_id`, `title`, `section`, `text`, 200-символьным
`snippet` и score слияния. Это единственная точка входа retrieval для `/ask`, `/list` и синтеза.

## Роутинг `/ask`: point vs synthesis

`route_question` ([router.py](../app/rag/router.py)) — **regex-эвристика, не LLM-вызов** — EN/RU
паттерны вроде *compare*, *difference*, *vs*, *survey*, *сравни*, *чем отлича*, *все статьи*
роутят в `synthesis`; всё остальное — `point`.

**point** → `hybrid_search(q, 5)` → `generate_answer` ([answer.py](../app/rag/answer.py)): вызов
Gemini (`gemini-flash-latest`, temperature 0.2, 3 ретрая), который обязан цитировать каждое
утверждение как `[arxiv_id]`, может писать `[id1][id2]`, обязан сказать, когда контекста
недостаточно, а не выдумывать, и отвечает на языке вопроса.

**synthesis** → `synthesize_answer` ([synthesis.py](../app/rag/synthesis.py)), map-reduce:

1. **Decompose** — один JSON-вызов Gemini разбивает вопрос на 2–4 подвопроса; при сбое откат к
   фиксированному эвристическому набору.
2. **Retrieve по каждому** — `hybrid_search` для каждого подвопроса, результаты в общий пул.
3. **Group** — дедуп чанков и группировка по `arxiv_id` (до 6 статей).
4. **Map** — один вызов Gemini на статью резюмирует, что говорит *именно эта* статья (≤4
   выдержки), с цитатой.
5. **Reduce** — один вызов Gemini пишет кросс-статейное сравнение из заметок по статьям; при сбое
   откат к `generate_answer` по общему пулу хитов.

Оба режима возвращают `(answer, hits)`; бот постит ответ, затем дедуплицированный блок **Sources**
(`arxiv_id`, заголовок, `arxiv.org/abs/{id}`).

## `/list` и откат к сниппетам

`/list <topic>` запускает `hybrid_search(topic, 15)`, дедупит по `arxiv_id` и показывает топ-10 как
листинг библиотеки (без генерации). В `/ask`, если генерация ответа падает, но хиты есть, бот
деградирует мягко — постит **сырые сниппеты** вместо ошибки.

## Текущие ограничения

- **Роутинг эвристический.** Интент не классифицирует LLM; сравнение без триггер-слова идёт по
  пути `point`.
- **Источники синтеза ограничены** (≤6 статей в map; 2 чанка/статью для списка Sources).
- **Dense всё ещё требует Gemini** для эмбеддинга запроса — full-text ветка единственная работает
  без него.
