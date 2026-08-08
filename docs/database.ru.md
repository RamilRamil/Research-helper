---
type: Reference
title: База данных — схема как собрана в scripts/*.sql
description: Две живые таблицы (papers, chunks), миграции halfvec + full-text + HNSW и backfill lifecycle.
tags: [database, postgres, pgvector, schema, migrations]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: scripts/init_db.sql
    title: таблица papers
  - resource: scripts/chunks_fts.sql
    title: full-text tsvector + GIN
  - resource: scripts/embedding_halfvec_hnsw.sql
    title: конвертация в halfvec + HNSW
  - resource: scripts/backfill_ingest_lifecycle.sql
    title: backfill legacy lifecycle
---

# База данных — схема как собрана

🇬🇧 [English version](database.md)

PostgreSQL 16 + pgvector. **Сегодня существуют две таблицы: `papers` и `chunks`.** Это описывает
то, что реально создают `scripts/*.sql`, что отличается от аспирационного
[plan/04-database-schema.md](plan/04-database-schema.md) (там добавлены `research_sessions` и
`chunk_feedback` — **не созданы**).

## `papers` — одна строка на статью arXiv

Из [scripts/init_db.sql](../scripts/init_db.sql): `arxiv_id` (уникальный, без суффикса версии) плюс
метаданные (`title`, `abstract`, `authors` jsonb, `published_at`, `pdf_url`), учёт ingest
(`pdf_local_path`, `page_count`, `text_chars`), enrichment (`summary_en`, `summary_ru`,
`tags text[]`), поля lifecycle (`ingest_status` по умолчанию `'pending'` — одно из
`pending | text_ok | indexed | failed` — и `ingest_error`) и provenance (`found_by_query`,
`search_query`). Индексы по `published_at`, `tags` (GIN) и `ingest_status`.

## `chunks` — сегменты текста для retrieval

Колонки: `id`, `paper_id` (FK → `papers` `ON DELETE CASCADE`), `chunk_index`, `section`, `text`,
`text_hash`, `token_count`, `embedding`, `created_at`, `UNIQUE (paper_id, chunk_index)`, плюс
`idx_chunks_paper_id`. Две миграции доводят её до текущей рабочей формы:

- **Full-text** ([chunks_fts.sql](../scripts/chunks_fts.sql)) — генерируемая stored-колонка
  `text_search tsvector` = `to_tsvector('english', coalesce(text, ''))`, с **GIN**-индексом
  `idx_chunks_text_search`. Питает `full_text_search`.
- **halfvec + HNSW** ([embedding_halfvec_hnsw.sql](../scripts/embedding_halfvec_hnsw.sql)) —
  `embedding` меняется с `vector(3072)` на **`halfvec(3072)`** на месте (без переэмбеддинга), с
  **HNSW**-индексом `idx_chunks_embedding_hnsw USING hnsw (embedding halfvec_cosine_ops)`.
  `halfvec` вдвое сокращает хранение и именно в него кастуется dense-запрос `<=>`.

## Backfill lifecycle

[backfill_ingest_lifecycle.sql](../scripts/backfill_ingest_lifecycle.sql) классифицирует legacy
строки `text_ok` до того, как ready-only retrieval становится надёжным: статья с ≥1 чанком и **без**
null-эмбеддингов → `indexed`; иначе → `failed` с сообщением о восстановлении. Запускается один раз
по существующим данным.

## Файлы миграций

| Файл | Эффект |
|---|---|
| [init_db.sql](../scripts/init_db.sql) | расширение `vector` + таблица `papers` + индексы |
| [add_chunks.sql](../scripts/add_chunks.sql) | `CREATE TABLE chunks` + `idx_chunks_paper_id` |
| [add_chunks_section.sql](../scripts/add_chunks_section.sql) | `ALTER TABLE chunks ADD COLUMN section` (идемпотентно) |
| [chunks_fts.sql](../scripts/chunks_fts.sql) | `text_search` tsvector + GIN |
| [embedding_halfvec_hnsw.sql](../scripts/embedding_halfvec_hnsw.sql) | `embedding → halfvec(3072)` + HNSW |
| [backfill_ingest_lifecycle.sql](../scripts/backfill_ingest_lifecycle.sql) | классификация legacy `text_ok` |

## Поднятие с нуля

Файлы миграций выше выполняются по порядку на свежей БД. `add_chunks.sql` раньше был **битым** —
заголовок `CREATE TABLE chunks (` был перезаписан на `CREATE INDEX ... USING hnsw (…); (`, оставляя
орфанный список колонок (невалидный SQL) и HNSW-по-`halfvec` оператор, шедший до конвертации в
halfvec. Он **пересобран** как обычный create таблицы (`embedding vector(3072)`), а full-text
колонка и halfvec/HNSW-конвертация оставлены отдельными шагами, которыми они и должны быть. Живая
таблица `chunks` уже соответствовала целевым колонкам, поэтому миграция данных не потребовалась.
