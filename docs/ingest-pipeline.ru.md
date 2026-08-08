---
type: Reference
title: Пайплайн ingest — от arxiv_id до проиндексированных чанков
description: /search → сохранение метаданных → advisory lock → скачивание → извлечение → чанкинг → эмбеддинг → indexed, и восстанавливаемый lifecycle.
tags: [ingest, pipeline, lifecycle, chunking, embeddings]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/tools/ingest_paper.py
    title: ingest_paper — оркестрация + advisory lock
  - resource: app/db/chunks.py
    title: save_chunks / embed_paper_chunks
  - resource: app/db/papers.py
    title: переходы lifecycle
---

# Пайплайн ingest — от `arxiv_id` до проиндексированных чанков

🇬🇧 [English version](ingest-pipeline.md)

Ingest превращает одну статью arXiv в проэмбежденные чанки, доступные для поиска. Он **явный и
per-paper**: `/search` только записывает метаданные; реальное скачивание + эмбеддинг происходят,
когда пользователь жмёт inline-кнопку. Sequence-диаграмма — в
[diagrams/ingest-flow.md](diagrams/ingest-flow.md).

## Триггер: сначала метаданные, ingest по запросу

`/search <topic>` вызывает arXiv, затем `save_paper` вставляет каждый результат с
`ingest_status = 'pending'` через `ON CONFLICT (arxiv_id) DO NOTHING` — поэтому повторные поиски
**идемпотентны** и не дублируют строки. В ответе статьи с кнопками `Add {id}` / `Indexed {id}`.
Нажатие `add:{id}` запускает `_ingest_one`, который пропускает уже `indexed` статьи, иначе
вызывает `ingest_paper` в рабочем потоке (`asyncio.to_thread`).

## `ingest_paper(arxiv_id)` по шагам

1. **Advisory lock.** `pg_try_advisory_lock(key)`, где `key` — process-independent sha256 от
   чистого arXiv id. Если lock держит другой ingest/reindex — `IngestBusyError` (работа не
   делается). Освобождается в `finally`.
2. **Скачивание.** `download_pdf` тянет `https://arxiv.org/pdf/{id}.pdf` через httpx в
   `data/papers/{id}.pdf`; если файл уже есть — переиспользуется.
3. **Извлечение.** `extract_text` (PyMuPDF, до 100 страниц) возвращает текст + число страниц. Если
   текст короче `MIN_TEXT_CHARS = 500` (пустой / сканированный PDF) — бросается исключение, статью
   нельзя проиндексировать.
4. **`text_ok`.** `update_paper_pdf` записывает `pdf_local_path`, `page_count`, `text_chars` и
   ставит `ingest_status = 'text_ok'`.
5. **Чанкинг.** `save_chunks` запускает section-aware чанкер (заголовки через regex по известным
   именам секций, затем скользящее окно 1000/200 внутри длинных секций), **удаляет существующие
   чанки** статьи и вставляет новые с `section`, `text_hash` и оценкой токенов.
6. **Эмбеддинг.** `embed_paper_chunks` эмбеддит каждый чанк с `embedding IS NULL` через Gemini
   (`gemini-embedding-001`, 3072-мерный), коммитит поштучно, спит ~0.7 с между вызовами и
   отступает ~45 с на HTTP 429.
7. **`indexed`.** `mark_paper_indexed` очищает `ingest_error` и ставит `ingest_status = 'indexed'`.

При успехе бот затем авто-запускает enrichment (концепт enrichment запланирован):
`enrich_and_save` пишет `summary_en` / `summary_ru` / `tags`. **Сбой enrichment не меняет
`ingest_status`** — проиндексированная статья остаётся доступной для поиска.

## Обработка ошибок

Любое исключение до `indexed` ловит вызывающий код, который зовёт `mark_paper_failed` с
обрезанной, очищенной от NUL строкой ошибки. **Скачанный PDF остаётся на диске** при сбоях —
меняется только статус в БД. `IngestBusyError` репортится как "busy", а не failure.

## Lifecycle и восстановление

```
pending ──текст извлечён──▶ text_ok ──чанки проэмбежены──▶ indexed
   │                           │
   └── сбой download/extract ──┴── сбой chunk/embed ──▶ failed
```

- **`indexed` терминален для нормального потока.** `/search` и кнопка `Add` пропускают его без
  мутации.
- **`/reindex <arxiv_id>`** — единственный путь восстановления. `prepare_reindex` принимает только
  `pending`, `text_ok` или `failed` и сбрасывает их в `pending`; он **отвергает `indexed`**
  (бросает исключение), чтобы рабочий индекс не пересобирался молча. Затем повторяет ту же
  последовательность ingest + enrich.

State-диаграмма (включая legacy backfill) — в
[diagrams/paper-lifecycle.md](diagrams/paper-lifecycle.md).

## Заметки и текущие ограничения

- **Повторный ingest переэмбеддивает.** `save_chunks` удаляет и пересоздаёт чанки, поэтому
  `text_hash` записывается, но **пока не используется** для пропуска неизменных чанков — каждый
  reindex платит полную цену эмбеддинга.
- **Advisory lock — на живой процесс.** sha256-ключ стабилен между рестартами; он защищает
  конкурентный ingest/reindex одного id внутри работающего бота.
- **Эмбеддинг — узкое место по квоте** (~30–80 чанков/статью × 1 вызов Gemini каждый), не
  скачивание.
