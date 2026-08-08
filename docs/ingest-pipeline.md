---
type: Reference
title: Ingest pipeline — from arxiv_id to indexed chunks
description: /search → save metadata → advisory lock → download → extract → chunk → embed → indexed, and the recoverable lifecycle.
tags: [ingest, pipeline, lifecycle, chunking, embeddings]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/tools/ingest_paper.py
    title: ingest_paper — orchestration + advisory lock
  - resource: app/db/chunks.py
    title: save_chunks / embed_paper_chunks
  - resource: app/db/papers.py
    title: lifecycle transitions
---

# Ingest pipeline — from `arxiv_id` to indexed chunks

🇷🇺 [Русская версия](ingest-pipeline.ru.md)

Ingest turns one arXiv paper into embedded, retrievable chunks. It is **explicit and per-paper**:
`/search` only records metadata; the actual download + embedding happens when the user taps an
inline button. The sequence diagram is in [diagrams/ingest-flow.md](diagrams/ingest-flow.md).

## Trigger: metadata first, ingest on demand

`/search <topic>` calls arXiv, then `save_paper` inserts each result with
`ingest_status = 'pending'` using `ON CONFLICT (arxiv_id) DO NOTHING` — so repeated searches are
**idempotent** and never duplicate rows. The reply lists papers with `Add {id}` / `Indexed {id}`
buttons. Tapping `add:{id}` runs `_ingest_one`, which skips already-`indexed` papers and otherwise
calls `ingest_paper` on a worker thread (`asyncio.to_thread`).

## `ingest_paper(arxiv_id)` step by step

1. **Advisory lock.** `pg_try_advisory_lock(key)` where `key` is a process-independent sha256
   derivation of the clean arXiv id. If another ingest/reindex holds it, raise `IngestBusyError`
   (no work done). Released in a `finally`.
2. **Download.** `download_pdf` fetches `https://arxiv.org/pdf/{id}.pdf` over httpx into
   `data/papers/{id}.pdf`; if the file already exists it is reused.
3. **Extract.** `extract_text` (PyMuPDF, up to 100 pages) returns text + page count. If the text is
   under `MIN_TEXT_CHARS = 500` (empty / scanned PDF) it raises — the paper cannot be indexed.
4. **`text_ok`.** `update_paper_pdf` records `pdf_local_path`, `page_count`, `text_chars` and sets
   `ingest_status = 'text_ok'`.
5. **Chunk.** `save_chunks` runs the section-aware chunker (headings via a regex over known section
   names, then a 1000/200 sliding window inside long sections), **deletes any existing chunks** for
   the paper, and inserts the new ones with `section`, `text_hash`, and a token estimate.
6. **Embed.** `embed_paper_chunks` embeds every chunk whose `embedding IS NULL` via Gemini
   (`gemini-embedding-001`, 3072-dim), committing per chunk, sleeping ~0.7 s between calls and
   backing off ~45 s on HTTP 429.
7. **`indexed`.** `mark_paper_indexed` clears `ingest_error` and sets `ingest_status = 'indexed'`.

On success the bot then auto-runs enrichment (see [enrichment](index.md#planned-additions-not-yet-written) —
concept planned): `enrich_and_save` writes `summary_en` / `summary_ru` / `tags`. **Enrichment
failure does not change `ingest_status`** — an indexed paper stays searchable.

## Failure handling

Any exception before `indexed` is caught by the caller, which calls `mark_paper_failed` with a
truncated, NUL-stripped error string. The **downloaded PDF stays on disk** across failures — only
the DB status changes. `IngestBusyError` is reported as "busy", not a failure.

## Lifecycle and recovery

```
pending ──text extracted──▶ text_ok ──chunks embedded──▶ indexed
   │                           │
   └── download/extract fail ──┴── chunk/embed fail ──▶ failed
```

- **`indexed` is terminal for normal flow.** `/search` and the `Add` button skip it without
  mutation.
- **`/reindex <arxiv_id>`** is the only recovery path. `prepare_reindex` accepts only `pending`,
  `text_ok`, or `failed` and resets them to `pending`; it **rejects `indexed`** (raises) so a
  working index is never silently rebuilt. It then re-runs the same ingest + enrich sequence.

The state diagram (including the legacy backfill) is in
[diagrams/paper-lifecycle.md](diagrams/paper-lifecycle.md).

## Notes and current limits

- **Re-ingest re-embeds.** `save_chunks` deletes and recreates chunks, so `text_hash` is recorded
  but **not yet used** to skip unchanged chunks — every reindex pays the full embedding cost.
- **The advisory lock is per running process.** The sha256 key is stable across restarts; it
  guards concurrent ingest/reindex of the same id within the live bot.
- **Embedding is the quota bottleneck** (~30–80 chunks/paper × 1 Gemini call each), not download.
