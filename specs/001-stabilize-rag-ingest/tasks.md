# Tasks: Stabilize RAG Ingest

**Input**: Design artifacts in `specs/001-stabilize-rag-ingest/`  
**Roadmap**: `docs/plan/05-build-roadmap.md` Phase 3.5  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/ingest-retrieval.md`, `quickstart.md`

## Dependencies

```text
Legacy inventory -> lifecycle functions -> lifecycle backfill -> ready-only retrieval
US1 duplicate avoidance and US2 observable lifecycle
  -> US3 explicit reindex + advisory lock
  -> US4 ready-only retrieval
  -> US5 HNSW type decision then index then query-plan verify
US6 section evaluation after at least five papers exist
```

## Implementation Strategy

MVP: complete legacy backfill, US1, US2, and US3 first. This stops quota loss, makes
state reliable, and makes recovery explicit under concurrency control. Then deliver
US4 and US5 before any hybrid retrieval work. Complete US6 after owner has five PDFs.

## Phase 1: Preparation

- [ ] T001 Read `specs/001-stabilize-rag-ingest/spec.md` and confirm scope matches `docs/plan/05-build-roadmap.md` Phase 3.5.
- [ ] T002 Inspect existing database schema and determine next unused migration number under `scripts/`.
- [ ] T003 Record state, chunk count, and null embedding count for exactly two legacy papers in `specs/001-stabilize-rag-ingest/implementation-notes.md`.

## Phase 2: Foundational Lifecycle

- [ ] T004 Add paper-state lookup and lifecycle update functions in `app/db/papers.py`.
- [ ] T005 Add successful finalization to `indexed` after all embedding work in `app/tools/ingest_paper.py`.
- [ ] T006 Add failed-state persistence with safe diagnostic text at ingest failure boundary in `app/bot/main.py`.
- [ ] T007 Create numbered lifecycle backfill migration in `scripts/NNN_backfill_ingest_lifecycle.sql` using rules from `specs/001-stabilize-rag-ingest/data-model.md`.
- [ ] T008 Apply approved lifecycle backfill before retrieval filter and record before/after classification for both legacy papers in `specs/001-stabilize-rag-ingest/implementation-notes.md`.

## Phase 3: User Story 1 - Avoid Duplicate Processing (P1)

**Goal**: normal topic search skips papers already in `indexed` state.

**Independent Test Criteria**: repeat same `/search`; previously indexed papers do not
download, delete chunks, or request embeddings again.

- [ ] T009 [US1] Use persisted paper state to gate normal ingest in `app/bot/main.py`.
- [ ] T010 [US1] Update `/search` outcome counts and text for new, skipped, and incomplete papers in `app/bot/main.py`.
- [ ] T011 [US1] Verify repeat-search behavior following `specs/001-stabilize-rag-ingest/quickstart.md` and record results in `specs/001-stabilize-rag-ingest/implementation-notes.md`.

## Phase 4: User Story 2 - Observe Reliable Ingest Result (P1)

**Goal**: every ingest ends in `indexed` or `failed`; retained PDF survives failure.

**Independent Test Criteria**: one successful and one controlled failed ingest show
correct state, diagnostic, and PDF retention.

- [ ] T012 [US2] Ensure successful lifecycle transition clears stale failure detail in `app/db/papers.py`.
- [ ] T013 [US2] Preserve PDF location when setting failed state in `app/db/papers.py`.
- [ ] T014 [US2] Verify success and failure lifecycle cases using `specs/001-stabilize-rag-ingest/quickstart.md`.

## Phase 5: User Story 3 - Recover an Incomplete Paper (P1)

**Goal**: owner explicitly resumes only `pending`, `text_ok`, or `failed` paper;
concurrent work on one arXiv ID is rejected.

**Independent Test Criteria**: `/reindex` resumes one failed and one text-ok paper;
rejects indexed paper; rejects concurrent second attempt without mutation.

- [ ] T015 [US3] Add reindex state transition and indexed-state rejection functions in `app/db/papers.py`.
- [ ] T016 [US3] Add per-paper PostgreSQL advisory lock around ingest in `app/tools/ingest_paper.py`.
- [ ] T017 [US3] Add whitelist-protected `/reindex <arxiv_id>` command using lock-aware ingest in `app/bot/main.py`.
- [ ] T018 [US3] Verify explicit reindex and concurrent busy rejection using `specs/001-stabilize-rag-ingest/quickstart.md`.

## Phase 6: User Story 4 - Search Only Ready Sources (P2)

**Goal**: retrieval returns chunks only from `indexed` papers.

**Independent Test Criteria**: matching chunks from `pending`, `text_ok`, and `failed`
records are excluded; matching indexed chunk is retained.

- [ ] T019 [US4] Add indexed-paper eligibility predicate to `app/db/search.py`.
- [ ] T020 [US4] Verify ready-only retrieval after lifecycle backfill and record query/result evidence in `specs/001-stabilize-rag-ingest/implementation-notes.md`.

## Phase 7: User Story 5 - Keep Retrieval Responsive (P2)

**Goal**: nearest-neighbor query has compatible HNSW index path.

**Independent Test Criteria**: query-plan review confirms index eligibility with current
vector dimensionality and distance operation.

- [ ] T021 [US5] Decide and document vector type plus distance operator for HNSW in `specs/001-stabilize-rag-ingest/implementation-notes.md`.
- [ ] T022 [US5] Create numbered HNSW migration in `scripts/NNN_add_chunks_hnsw.sql` matching the documented type/operator.
- [ ] T023 [US5] Align vector distance expression with HNSW index type in `app/db/search.py`.
- [ ] T024 [US5] Apply approved migration, inspect query plan, and document parameters in `specs/001-stabilize-rag-ingest/implementation-notes.md`.

## Phase 8: User Story 6 - Evaluate PDF Sections (P3)

**Goal**: decide from evidence whether PDF-first section labels remain acceptable.

**Independent Test Criteria**: review at least five papers and record a clear retain or
LaTeX-follow-up conclusion.

- [ ] T025 [US6] Ensure at least five stored papers exist; owner may add papers via `/search` before evaluation.
- [ ] T026 [US6] Query section counts for five varied papers using stored `chunks.section`.
- [ ] T027 [US6] Compare queried labels against visible headings in five PDFs under `data/papers/`.
- [ ] T028 [US6] Create `specs/001-stabilize-rag-ingest/section-evaluation.md` with coverage, heading errors, and retain-PDF or LaTeX-follow-up decision.

## Phase 9: Polish and Handoff

- [ ] T029 Review `specs/001-stabilize-rag-ingest/contracts/ingest-retrieval.md` against final code and update contract if behavior changed.
- [ ] T030 Update `RAG_UPGRADE_PLAN.md` baseline to state that section-aware chunking is implemented and Phase 3.5 lifecycle stabilization is complete.
- [ ] T031 Confirm `docs/plan/05-build-roadmap.md` Phase 3.5 verify list matches recorded evidence in `specs/001-stabilize-rag-ingest/implementation-notes.md`.
- [ ] T032 Re-read `specs/001-stabilize-rag-ingest/checklists/requirements.md` and record final verification status in `specs/001-stabilize-rag-ingest/implementation-notes.md`.

## Parallel Opportunities

- T021-T022 can begin after T002 while lifecycle work T004-T018 proceeds, but T023-T024 wait for T021.
- T025 can begin after T003; T026-T028 wait until five papers exist.
- T029-T032 depend on all relevant earlier tasks.

## Suggested MVP Scope

T001-T018: lifecycle backfill, stable duplicate avoidance, observable lifecycle,
explicit recovery, and per-paper concurrency lock. This removes repeated embedding cost
before retrieval-quality work.
