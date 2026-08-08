---
type: Diagram
title: Ingest flow — Add button to indexed
description: One paper through ingest_paper — advisory lock, download, extract, chunk, embed, auto-enrich.
tags: [diagram, sequence, ingest]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/tools/ingest_paper.py
    title: ingest_paper
  - resource: app/bot/main.py
    title: _ingest_one / on_add_one
---

# Ingest flow — `Add` button to `indexed`

🇷🇺 [Русская версия](ingest-flow.ru.md)

One paper from the inline `Add` button to `indexed`, then auto-enrichment. Prose in
[../ingest-pipeline.md](../ingest-pipeline.md).

```mermaid
sequenceDiagram
    participant U as User (Telegram)
    participant Bot as bot/main.py
    participant Ing as ingest_paper
    participant AX as arXiv
    participant FS as data/papers
    participant Gem as Gemini
    participant PG as PostgreSQL

    U->>Bot: tap "Add {id}" (callback add:{id})
    Bot->>PG: get_paper_status(id)
    alt already indexed
        Bot-->>U: skipped (already indexed)
    else ingest
        Bot->>Ing: ingest_paper(id) [asyncio.to_thread]
        Ing->>PG: pg_try_advisory_lock(key)
        alt lock held by another run
            Ing-->>Bot: IngestBusyError → "busy"
        else acquired
            Ing->>AX: download PDF (reuse if on disk)
            AX-->>FS: {id}.pdf
            Ing->>Ing: extract_text (PyMuPDF) — under 500 chars ⇒ fail
            Ing->>PG: update_paper_pdf ⇒ text_ok
            Ing->>PG: save_chunks (DELETE old + INSERT)
            loop each chunk WHERE embedding IS NULL
                Ing->>Gem: embed_text (429 ⇒ backoff ~45s)
                Ing->>PG: UPDATE chunk SET embedding
            end
            Ing->>PG: mark_paper_indexed ⇒ indexed
            Ing->>PG: pg_advisory_unlock (finally)
        end
        Bot->>Gem: enrich_and_save (auto, failure ≠ status change)
        Bot-->>U: "[id] indexed ok + enriched"
    end
```

- **Failure before `indexed`** ⇒ caller runs `mark_paper_failed` (safe error); the PDF stays on
  disk. `IngestBusyError` is reported as "busy", not a failure.
- **`/reindex`** enters the same `ingest_paper` sequence after `prepare_reindex` resets a
  `pending` / `text_ok` / `failed` paper to `pending` (never `indexed`).
