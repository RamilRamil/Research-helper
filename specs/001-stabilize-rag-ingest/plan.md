# Implementation Plan: Stabilize RAG Ingest

## Technical Context

| Area | Current state | Planned change |
|---|---|---|
| Bot command | `/search` calls ingest for every result | Gate ingest using persisted paper state. |
| Metadata persistence | Raw `psycopg`, existing `papers` states | Add state lookup, success finalization, and failure persistence. |
| Chunk persistence | Delete and recreate all chunks | Preserve this behavior only for future explicit reindex; normal search avoids it. |
| Embeddings | Gemini `gemini-embedding-001`, 3072 dimensions | No model change. Finalize paper only after embedding loop succeeds. |
| Retrieval | pgvector cosine search without eligibility filter/index | Filter to `indexed`; create compatible HNSW index. |
| PDF section labels | Regex over PyMuPDF text | Do not change parser yet; evaluate quality on five PDFs. |
| Legacy data | Two existing papers may be `text_ok` | Classify both before ready-only retrieval rollout. |
| Concurrency | `/search` and `/reindex` can overlap | Per-paper PostgreSQL advisory lock. |
| Roadmap home | `docs/plan/05-build-roadmap.md` Phase 3.5 | This Spec Kit feature is that phase's execution plan. |

## Constitution Check

| Principle | Status | Evidence |
|---|---|---|
| Preserve user data | Pass | Failed indexing retains downloaded PDF. |
| Repeatable ingest | Pass | `indexed` papers are skipped; incomplete papers require explicit `/reindex`. |
| Explicit lifecycle | Pass | State transitions and failures are persisted. |
| Grounded retrieval | Pass | Only indexed papers are eligible. |
| Measure before complexity | Pass | Section validation precedes LaTeX follow-up. |
| No unapproved dependencies | Pass | Uses existing Python/Postgres stack. |

## Design

### 1. Read lifecycle state before normal ingest

Extend paper repository with a lookup returning paper identifier and current
`ingest_status`. In `/search`:

- new paper: save then ingest;
- existing `indexed` paper: increment skipped count and do not ingest;
- existing non-ready paper: report it distinctly; do not silently overwrite it.

### 1a. Recover incomplete ingest explicitly

Add `/reindex <arxiv_id>` under existing whitelist. It may operate only on `pending`,
`text_ok`, or `failed` papers:

- transition selected paper to `pending`;
- run ingest and record final state;
- retain local PDF on failure.

Reject `indexed` paper without mutation. Current chunk storage replaces chunks in place;
safe reindexing of an indexed paper needs staged/versioned chunks and is deferred.

### 1b. Prevent concurrent ingest of one paper

Wrap ingest used by `/search` and `/reindex` with a PostgreSQL advisory lock keyed by
arXiv ID. If lock acquisition fails, return a busy response and leave all stored data
unchanged. Do not introduce an `ingesting` status for this feature.

### 2. Persist lifecycle transitions

Keep `save_paper` as creator of `pending` records. After successful text extraction,
continue using `text_ok`. After every chunk embedding succeeds, update paper to
`indexed`, clear `ingest_error`, and refresh `updated_at`. Summaries and tags remain
out of scope; readiness does not depend on enrichment.

At command boundary, catch ingest exception, record `failed` and safe error text, then
send concise Telegram error. Do not remove the local PDF.

### 3. Backfill legacy papers before ready-only retrieval

Before adding retrieval filter, inspect both existing paper rows and record current
state, chunk count, and null-embedding count. Migration policy:

- `text_ok` with at least one chunk and no null embedding: mark `indexed`;
- `text_ok` with empty/incomplete chunks: mark `failed` with
  `legacy incomplete ingest; run /reindex`;
- `pending` and `failed`: retain state, require explicit `/reindex`.

Record exact before/after classification in implementation notes. Do not enable
ready-only retrieval until this evidence exists.

### 4. Make ready-only retrieval explicit

Add `p.ingest_status = 'indexed'` to retrieval predicate. Preserve result payload and
current cosine metric.

### 5. Add compatible vector index

Decide vector type and distance operator first, then create a dedicated SQL migration
in `scripts/` for HNSW on `chunks.embedding` using the same type/operator class used by
retrieval. Avoid a `halfvec` cast that cannot use an index built on `vector`.

Before selecting HNSW parameters, inspect installed pgvector version and corpus size.
Document selected parameters and query-plan result in implementation notes.

### 6. Evaluate section labels

Owner may add papers so at least five PDFs exist. Use read-only SQL inspection and
manual PDF review. Record results in a dated evaluation note under this feature before
scheduling LaTeX-first work.

## File-Level Changes

| File | Change |
|---|---|
| `app/db/papers.py` | Lookup state; mark paper indexed; mark paper failed; reindex transitions. |
| `app/tools/ingest_paper.py` | Finalize `indexed` after embeddings; advisory lock around ingest. |
| `app/bot/main.py` | Gate normal ingest; incomplete-only `/reindex`; busy response on lock conflict. |
| `app/db/search.py` | Restrict results to indexed papers; align operator/cast to new index. |
| `scripts/NNN_backfill_ingest_lifecycle.sql` | Classify legacy records before retrieval filtering. |
| `scripts/NNN_add_chunks_hnsw.sql` | Add HNSW index without changing existing data. |
| `specs/001-stabilize-rag-ingest/` | Record section evaluation and query-plan evidence. |

## Verification

1. Legacy backfill classifies both existing papers before retrieval filtering.
2. First `/search`: new papers finish in `indexed` state.
3. Same `/search`: indexed papers skip download, chunk recreation, and embedding.
4. `/reindex` resumes incomplete paper and rejects `indexed` paper without mutation.
5. Concurrent `/search` or `/reindex` on one arXiv ID is rejected without mutation.
6. Controlled ingest failure: paper becomes `failed`, error is persisted, stored PDF
   remains.
7. Search fixture with non-ready chunks: no non-ready result returned.
8. `EXPLAIN ANALYZE`: nearest-neighbor query is index-eligible after migration.
9. Five-PDF review: explicit retain-PDF or LaTeX-follow-up decision.

## Deferred Work

Aligned with `docs/plan/05-build-roadmap.md`:

- Phase 4: paper enrichment (summaries and tags);
- Phase 5: hybrid full-text plus dense retrieval;
- Phase 6: LLM answers with citations;
- Phase 7: synthesis routing;
- Phase 8: LangGraph agent;
- later: LaTeX-first ingest, visual/diagram retrieval, PageIndex, or T-Search.
