---
type: Diagram
title: Поток ingest — от кнопки Add до indexed
description: Одна статья через ingest_paper — advisory lock, скачивание, извлечение, чанкинг, эмбеддинг, авто-enrich.
tags: [diagram, sequence, ingest]
lang: ru
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

# Поток ingest — от кнопки `Add` до `indexed`

🇬🇧 [English version](ingest-flow.md)

Одна статья от inline-кнопки `Add` до `indexed`, затем авто-enrichment. Проза в
[../ingest-pipeline.ru.md](../ingest-pipeline.ru.md).

```mermaid
sequenceDiagram
    participant U as Пользователь (Telegram)
    participant Bot as bot/main.py
    participant Ing as ingest_paper
    participant AX as arXiv
    participant FS as data/papers
    participant Gem as Gemini
    participant PG as PostgreSQL

    U->>Bot: жмёт "Add {id}" (callback add:{id})
    Bot->>PG: get_paper_status(id)
    alt уже indexed
        Bot-->>U: skipped (already indexed)
    else ingest
        Bot->>Ing: ingest_paper(id) [asyncio.to_thread]
        Ing->>PG: pg_try_advisory_lock(key)
        alt lock держит другой запуск
            Ing-->>Bot: IngestBusyError → "busy"
        else захвачен
            Ing->>AX: скачать PDF (переиспользовать, если на диске)
            AX-->>FS: {id}.pdf
            Ing->>Ing: extract_text (PyMuPDF) — меньше 500 символов ⇒ fail
            Ing->>PG: update_paper_pdf ⇒ text_ok
            Ing->>PG: save_chunks (DELETE старые + INSERT)
            loop каждый чанк WHERE embedding IS NULL
                Ing->>Gem: embed_text (429 ⇒ backoff ~45s)
                Ing->>PG: UPDATE chunk SET embedding
            end
            Ing->>PG: mark_paper_indexed ⇒ indexed
            Ing->>PG: pg_advisory_unlock (finally)
        end
        Bot->>Gem: enrich_and_save (авто, сбой ≠ смена статуса)
        Bot-->>U: "[id] indexed ok + enriched"
    end
```

- **Сбой до `indexed`** ⇒ вызывающий код запускает `mark_paper_failed` (безопасная ошибка); PDF
  остаётся на диске. `IngestBusyError` репортится как "busy", не failure.
- **`/reindex`** входит в ту же последовательность `ingest_paper` после того, как `prepare_reindex`
  сбрасывает `pending` / `text_ok` / `failed` статью в `pending` (никогда не `indexed`).
