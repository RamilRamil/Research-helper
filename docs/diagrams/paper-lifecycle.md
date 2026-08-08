---
type: Diagram
title: Paper lifecycle — ingest_status state machine
description: pending → text_ok → indexed | failed, explicit reindex, and the legacy backfill.
tags: [diagram, state, lifecycle, ingest]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/db/papers.py
    title: lifecycle transitions
  - resource: scripts/backfill_ingest_lifecycle.sql
    title: legacy backfill
---

# Paper lifecycle — `ingest_status`

🇷🇺 [Русская версия](paper-lifecycle.ru.md)

The `ingest_status` state machine. Prose in [../ingest-pipeline.md](../ingest-pipeline.md).

```mermaid
stateDiagram-v2
    [*] --> pending: save_paper (metadata)
    pending --> text_ok: update_paper_pdf (text extracted)
    text_ok --> indexed: mark_paper_indexed (all chunks embedded)
    pending --> failed: download / extract error
    text_ok --> failed: chunk / embed error
    failed --> pending: /reindex (prepare_reindex)
    text_ok --> pending: /reindex
    pending --> pending: /reindex

    note right of indexed
        terminal for /search and Add;
        the only status eligible for retrieval;
        /reindex is rejected
    end note
```

- **Ready-only retrieval.** `search_chunks` / `full_text_search` only read `indexed` papers.
- **Recovery is explicit.** `/reindex` accepts `pending` / `text_ok` / `failed` and resets to
  `pending`; `indexed` is rejected so a working index is never silently rebuilt.
- **Legacy backfill** ([backfill_ingest_lifecycle.sql](../../scripts/backfill_ingest_lifecycle.sql)):
  pre-existing `text_ok` rows with ≥1 chunk and no null embedding → `indexed`; otherwise → `failed`.
  The local PDF is retained through every transition.
