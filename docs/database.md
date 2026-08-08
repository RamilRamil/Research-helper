---
type: Reference
title: Database — schema as built in scripts/*.sql
description: The two live tables (papers, chunks), the halfvec + full-text + HNSW migrations, and the lifecycle backfill.
tags: [database, postgres, pgvector, schema, migrations]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: scripts/init_db.sql
    title: papers table
  - resource: scripts/chunks_fts.sql
    title: full-text tsvector + GIN
  - resource: scripts/embedding_halfvec_hnsw.sql
    title: halfvec conversion + HNSW
  - resource: scripts/backfill_ingest_lifecycle.sql
    title: legacy lifecycle backfill
---

# Database — schema as built

🇷🇺 [Русская версия](database.ru.md)

PostgreSQL 16 + pgvector. **Two tables exist today: `papers` and `chunks`.** This documents what
`scripts/*.sql` actually create, which differs from the aspirational
[plan/04-database-schema.md](plan/04-database-schema.md) (that one adds `research_sessions` and
`chunk_feedback` — **not created**).

## `papers` — one row per arXiv paper

From [scripts/init_db.sql](../scripts/init_db.sql): `arxiv_id` (unique, version-stripped) plus
metadata (`title`, `abstract`, `authors` jsonb, `published_at`, `pdf_url`), ingest bookkeeping
(`pdf_local_path`, `page_count`, `text_chars`), enrichment (`summary_en`, `summary_ru`,
`tags text[]`), the lifecycle fields (`ingest_status` default `'pending'` — one of
`pending | text_ok | indexed | failed` — and `ingest_error`), and provenance (`found_by_query`,
`search_query`). Indexed on `published_at`, `tags` (GIN), and `ingest_status`.

## `chunks` — text segments for retrieval

Columns: `id`, `paper_id` (FK → `papers` `ON DELETE CASCADE`), `chunk_index`, `section`, `text`,
`text_hash`, `token_count`, `embedding`, `created_at`, `UNIQUE (paper_id, chunk_index)`, plus
`idx_chunks_paper_id`. Two migrations bring it to its current, working shape:

- **Full-text** ([chunks_fts.sql](../scripts/chunks_fts.sql)) — a generated stored column
  `text_search tsvector` = `to_tsvector('english', coalesce(text, ''))`, with a **GIN** index
  `idx_chunks_text_search`. Drives `full_text_search`.
- **halfvec + HNSW** ([embedding_halfvec_hnsw.sql](../scripts/embedding_halfvec_hnsw.sql)) —
  `embedding` is altered from `vector(3072)` to **`halfvec(3072)`** in place (no re-embed), with an
  **HNSW** index `idx_chunks_embedding_hnsw USING hnsw (embedding halfvec_cosine_ops)`. `halfvec`
  halves storage and is what the dense `<=>` query casts to.

## Lifecycle backfill

[backfill_ingest_lifecycle.sql](../scripts/backfill_ingest_lifecycle.sql) classifies legacy
`text_ok` rows before ready-only retrieval is trusted: a paper with ≥1 chunk and **no** null
embedding → `indexed`; otherwise → `failed` with a recovery message. Run once against existing data.

## Migration files

| File | Effect |
|---|---|
| [init_db.sql](../scripts/init_db.sql) | `vector` extension + `papers` table + indexes |
| [add_chunks.sql](../scripts/add_chunks.sql) | `CREATE TABLE chunks` + `idx_chunks_paper_id` |
| [add_chunks_section.sql](../scripts/add_chunks_section.sql) | `ALTER TABLE chunks ADD COLUMN section` (idempotent) |
| [chunks_fts.sql](../scripts/chunks_fts.sql) | `text_search` tsvector + GIN |
| [embedding_halfvec_hnsw.sql](../scripts/embedding_halfvec_hnsw.sql) | `embedding → halfvec(3072)` + HNSW |
| [backfill_ingest_lifecycle.sql](../scripts/backfill_ingest_lifecycle.sql) | classify legacy `text_ok` rows |

## Provisioning from scratch

The migration files above run cleanly in order against a fresh database. `add_chunks.sql` previously
shipped **corrupted** — the `CREATE TABLE chunks (` header had been overwritten by an
`CREATE INDEX ... USING hnsw (…); (`, leaving an orphan column list that was invalid SQL (and an
HNSW-on-`halfvec` op that predated the halfvec conversion). It has been **rebuilt** as a plain table
create (`embedding vector(3072)`), with the full-text column and the halfvec/HNSW conversion kept as
the separate follow-ups they require. The live `chunks` table already matched the intended columns,
so no data migration was needed.
