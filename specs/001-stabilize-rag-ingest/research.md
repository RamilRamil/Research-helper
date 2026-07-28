# Research: Stabilize RAG Ingest

## Decision 1: gate normal ingest by lifecycle state

**Decision**: normal `/search` ingests only newly discovered papers. Existing papers
in `indexed` state are skipped. Incomplete papers require explicit `/reindex`.

**Rationale**: `app/bot/main.py` currently invokes ingest even when `save_paper`
reports that a paper already exists. `app/db/chunks.py` then deletes every existing
chunk, forcing embedding work again. State-gated processing preserves quota and makes
normal discovery idempotent.

**Alternatives considered**:
- Compare downloaded file bytes on every search: still downloads the file and does not
  solve unnecessary embedding calls.
- Reindex all papers by default: only suitable for an explicit maintenance command.

## Decision 1a: explicit recovery for incomplete papers

**Decision**: provide `/reindex <arxiv_id>` only for papers in `pending`, `text_ok`,
or `failed`. Reject requests for `indexed` papers.

**Rationale**: normal search remains idempotent while an owner can recover one
incomplete paper. Rejecting `indexed` avoids deleting a working representation because
current chunk persistence replaces chunks in place rather than staging a new version.

**Alternatives considered**:
- Automatic retries in normal search: can repeatedly spend quota on permanent errors.
- Reindex every state: needs staged/versioned chunks to prevent a failed replacement
  from destroying a working index.

## Decision 1b: per-paper advisory lock for concurrent ingest

**Decision**: take a PostgreSQL advisory lock keyed by arXiv ID for the duration of
`ingest_paper` used by `/search` and `/reindex`. If the lock is held, reject the second
attempt with a visible busy message and make no mutations.

**Rationale**: chunk delete/insert plus per-chunk embedding commits are not
transaction-safe across concurrent handlers. An advisory lock prevents double
embedding spend and corrupted partial chunk sets without a new schema state.

**Alternatives considered**:
- Add an `ingesting` status: requires new lifecycle value and careful crash cleanup.
- Process-local mutex: insufficient if more than one bot process runs.

## Decision 2: make paper state authoritative

**Decision**: use existing states `pending`, `text_ok`, `indexed`, and `failed`;
store failure detail in existing `ingest_error`.

**Rationale**: schema already provides both fields. Current update stops at `text_ok`
even after embeddings are written; therefore normal reuse and retrieval filtering
cannot distinguish ready records.

**Alternatives considered**:
- Infer readiness by counting non-null embeddings: costly and ambiguous after partial
  failures.
- Add a second state table: adds complexity without a current need.

## Decision 2a: backfill legacy records before ready-only search

**Decision**: classify every existing `text_ok` legacy paper before applying
ready-only retrieval. A paper with one or more chunks and no null embeddings becomes
`indexed`; every other legacy record becomes `failed` with actionable diagnostic.

**Rationale**: current code never writes `indexed`. Enabling a strict retrieval filter
without backfill would hide the entire existing library.

**Alternatives considered**:
- Temporarily treat `text_ok` as searchable: perpetuates ambiguous readiness and can
  return partially embedded data.
- Mark all `text_ok` papers indexed: silently accepts partial or empty index state.

## Decision 3: retain PDF independently from index outcome

**Decision**: after successful download, retain local PDF even if text extraction or
embedding fails.

**Rationale**: personal PDF library is stated product requirement. A later retry may
reprocess retained file without another network download.

**Alternatives considered**:
- Delete failed PDFs: conflicts with library goal and loses evidence needed to debug
  parser failures.

## Decision 4: add approximate-nearest-neighbor index before retrieval expansion

**Decision**: add an HNSW index that matches current 3072-dimensional vector storage
and distance operator; validate it with a query plan.

**Rationale**: `scripts/add_chunks.sql` has index only on `paper_id`; vector ordering
otherwise scans stored chunks. Hybrid search should not be designed atop an
unmeasured unindexed baseline.

**Alternatives considered**:
- IVFFlat: valid for large, static collections but needs tuning and training data.
- Delay indexing: acceptable only while corpus is trivially small; conflicts with
  planned personal library growth.

## Decision 5: measure existing PDF section labels before source-parser change

**Decision**: sample at least five stored papers and record label coverage plus
heading errors. Owner may add papers before evaluation so the sample is reachable.
Start separate LaTeX-first specification only if result is poor.

**Rationale**: section-aware chunking now exists in `app/rag/chunker.py`; its regex
expects complete heading lines and may fail on PDF layout. This is a quality question,
not an assumption. Roadmap Phase 3.5 (`docs/plan/05-build-roadmap.md`) requires this
gate before LaTeX-first work.

**Alternatives considered**:
- Immediately adopt LaTeX source: adds parser, archive handling, storage, and failure
  paths before evidence shows current path is inadequate.
- Reduce sample to the two legacy papers: too weak to justify a source-parser change.
