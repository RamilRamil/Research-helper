---
type: Diagram
title: Lifecycle статьи — машина состояний ingest_status
description: pending → text_ok → indexed | failed, явный reindex и legacy backfill.
tags: [diagram, state, lifecycle, ingest]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/db/papers.py
    title: переходы lifecycle
  - resource: scripts/backfill_ingest_lifecycle.sql
    title: legacy backfill
---

# Lifecycle статьи — `ingest_status`

🇬🇧 [English version](paper-lifecycle.md)

Машина состояний `ingest_status`. Проза в [../ingest-pipeline.ru.md](../ingest-pipeline.ru.md).

```mermaid
stateDiagram-v2
    [*] --> pending: save_paper (метаданные)
    pending --> text_ok: update_paper_pdf (текст извлечён)
    text_ok --> indexed: mark_paper_indexed (все чанки проэмбежены)
    pending --> failed: ошибка download / extract
    text_ok --> failed: ошибка chunk / embed
    failed --> pending: /reindex (prepare_reindex)
    text_ok --> pending: /reindex
    pending --> pending: /reindex

    note right of indexed
        терминален для /search и Add;
        единственный статус, доступный для retrieval;
        /reindex отвергается
    end note
```

- **Ready-only retrieval.** `search_chunks` / `full_text_search` читают только `indexed` статьи.
- **Восстановление явное.** `/reindex` принимает `pending` / `text_ok` / `failed` и сбрасывает в
  `pending`; `indexed` отвергается, чтобы рабочий индекс не пересобирался молча.
- **Legacy backfill** ([backfill_ingest_lifecycle.sql](../../scripts/backfill_ingest_lifecycle.sql)):
  существующие `text_ok` строки с ≥1 чанком и без null-эмбеддингов → `indexed`; иначе → `failed`.
  Локальный PDF сохраняется при всех переходах.
