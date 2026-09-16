# Implementation Plan: Staged Reindex

**Feature**: `009-staged-reindex`

## Technical Context

- Language: Python 3.12 in `app/`
- Store: PostgreSQL `papers` + `chunks` (pgvector)
- No new packages
- Command: existing `/reindex`

## Constitution Check

- I: code from this spec/tasks
- III: `/search` still skips `indexed`; rebuild is explicit
- V: one chunks table; live gen filter, not a second index product
- VI: SQL in `scripts/chunk_gen.sql`

## Design

- `papers.chunk_gen` and `chunks.chunk_gen`, default 0 (existing rows live).
- Unique key `(paper_id, chunk_gen, chunk_index)`.
- Retrieval: `ingest_status = indexed` AND `c.chunk_gen = p.chunk_gen`.
- Indexed rebuild: write gen+1, embed, swap `papers.chunk_gen`, delete other gens.
- Fail: delete gen+1 only; keep status `indexed`; set `ingest_error`. Do not `mark_paper_failed`.
- Incomplete `/reindex`: unchanged (`prepare_reindex` + ingest, still deletes all chunks for that paper).
- `/reindex indexed`: sequential rebuild of all indexed ids (P2).
