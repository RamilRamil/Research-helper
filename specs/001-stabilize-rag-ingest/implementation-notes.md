# Implementation notes: 001-stabilize-rag-ingest

**Date:** 2026-09-09  
**DB:** local Compose `db` healthy (`pgvector` pg16, port 5433). App image used for Python deps.

## T001 / T002

Scope = Phase 3.5. SQL lives in unnumbered `scripts/backfill_ingest_lifecycle.sql` and
`scripts/embedding_halfvec_hnsw.sql` (no extra numbered copies).

## T003 two papers (live)

| arxiv_id | ingest_status | chunks | null embeddings |
|----------|---------------|--------|-----------------|
| 2604.16548 | indexed | 74 | 0 |
| 2607.20124 | failed | 85 | 85 |

Corpus: 60 papers. Histogram before/after backfill: failed 12, indexed 19, pending 29
(unchanged). No `text_ok` rows left; backfill was a no-op.

## T008

Applied `scripts/backfill_ingest_lifecycle.sql`. Counts unchanged. Two-paper table above
is after apply.

## T018 concurrent lock

Held `pg_try_advisory_lock` for `2604.16548`, then `ingest_paper`. Result: `IngestBusyError`.
Chunk count stayed 74, status stayed `indexed`.

## T020 ready-only

Indexed chunks with embedding: 2094. Chunks whose parent is not `indexed`: 215.
Retrieval SQL requires `p.ingest_status = 'indexed'` (`app/db/search.py`).

## T021 / T024 HNSW

Column type: `halfvec(3072)`. Indexes: `idx_chunks_embedding`, `idx_chunks_embedding_hnsw`.
Query uses `<=>` with `::halfvec(3072)`.

Default `EXPLAIN` on join+order (small corpus ~2k chunks): Seq Scan + Sort (planner
prefers seq scan).

`SET enable_seqscan = off` on embedding-only ORDER BY: `Index Scan using
idx_chunks_embedding_hnsw` with `Order By: (embedding <=> $0)`. Index is eligible;
not chosen at current size with join.

## T018 indexed reject

`prepare_reindex('2604.16548')` -> `ValueError: paper already indexed: 2604.16548`.
Status remained `indexed`.

## T032 checklist

`checklists/requirements.md` still complete for spec quality. T011 recorded 2026-09-09
from owner Telegram logs.

## T011 / Telegram `/search`

Topic: `memory injection`.

1. 01:35 first search: 10 new, 0 already in DB; all `pending`. Then Add all ingest
   (01:41-01:59): ten `indexed ok`; enrich 503/429 on three ids (ingest status kept).
2. 07:43 repeat search: footer `8 new, 2 already in DB`. List shows
   `2609.04875` and `2609.04190` as `(indexed)`; eight other ids `pending` (new arXiv
   hits, not re-ingest of the old ten). Metadata skip for the two indexed papers
   matches US1.

Footer text `already in DB` is the pre-T010 wording; skip semantics hold. Rebuild bot
to get `skipped indexed` / `incomplete` counts.

07:43 Add all on the new 10-hit list will ingest eight *new* papers (plus skip two
indexed). That is not a T011 failure; it spends embed quota on new ids.

## T014 failure case

Existing `2607.20124` is `failed` with all-null embeddings; PDF `data/papers/2607.20124.pdf`
present. No new induced failure this session.
