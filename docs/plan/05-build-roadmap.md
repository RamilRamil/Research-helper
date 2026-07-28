# Build Roadmap

Self-assembly guide: build layers bottom-up. Agent (LangGraph) is the last layer, not the first.

---

## Phase 0: Skeleton (days 1-2)

**Goal:** Docker runs, bot responds, empty DB.

Tasks:
1. docker-compose: `app` + `postgres` with `pgvector/pgvector` image
2. aiogram: `/start`, whitelist by `user_id`
3. `psycopg` + versioned SQL scripts: create `papers` table
4. `.env`: `TELEGRAM_TOKEN`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`, `ALLOWED_USER_ID`

**Verify:** message to bot -> reply; Postgres table exists.

---

## Phase 1: arXiv without LLM (days 3-4)

**Goal:** understand external data source separately from agent.

Tasks:
1. `build_query(topic, date_from, date_to) -> str`
2. `arxiv` library search, max_results=20, sort by submitted date
3. Save metadata to `papers` with `ingest_status='pending'`

**Verify:** CLI script prints 5 arxiv_id + titles; bot `/search_test` does the same.

**Learn:** arXiv API, date normalization, dedupe by arxiv_id.

---

## Phase 2: PDF pipeline (days 5-7)

**Goal:** from arxiv_id to text on disk.

Tasks:
1. Download PDF to `data/papers/{arxiv_id}.pdf`; retain stored PDF on later failures.
2. Extract text with PyMuPDF.
3. Validate text length; update `pdf_local_path`, `page_count`, `text_chars`.
4. Set `text_ok` only after successful extraction; persist `failed` plus safe error on
   download/extraction failure.

**Verify:** one paper -> stored PDF -> extracted text inspected through approved
read-only check.

**Learn:** two-column PDF layout, empty text on scanned PDFs.

---

## Phase 3: Chunking + embeddings (days 8-10)

**Goal:** RAG-ready DB without LangGraph.

Tasks:
1. Chunker: split detected PDF sections, then window long sections at
   `CHUNK_SIZE=1000`, `OVERLAP=200`.
2. Create `chunks` table with `section`, `text_hash`, and active embedding dimension.
3. Gemini embeddings per chunk; retry on 429.
4. Mark paper `indexed` only after every chunk embedding succeeds.

**Verify:** chunk count > 0; section labels exist; every `indexed` paper has no null
chunk embedding.

**Note:** `text_hash` is recorded now but cannot skip re-embedding while reindex
deletes/recreates chunks. Do not promise that optimization before staged/versioned
reindex exists.

---

## Phase 3.5: Stabilize ingest lifecycle

**Goal:** repeated discovery is idempotent; incomplete papers are recoverable; retrieval
never exposes incomplete source data.

**Spec Kit:** [`specs/001-stabilize-rag-ingest/`](../../specs/001-stabilize-rag-ingest/)

Tasks:
1. Legacy backfill: classify existing records before adding ready-only retrieval.
2. `/search`: ingest only new papers; skip `indexed`; report incomplete records.
3. `/reindex <arxiv_id>`: manually resume only `pending`, `text_ok`, or `failed`;
   reject `indexed` without mutation.
4. Add per-paper advisory lock for `/search` and `/reindex`.
5. Restrict retrieval to `indexed` papers.
6. Create HNSW index only after query vector type/operator matches stored vector.
7. Evaluate section detection on at least five PDFs before planning LaTeX-first ingest.

**Verify:** repeat search makes zero PDF/embedding calls for indexed papers; legacy rows
are classified; concurrent work on one arXiv ID is rejected; ready-only retrieval and
HNSW query plan are confirmed.

---

## Phase 4: Paper enrichment (summaries and tags)

**Goal:** paper cards for Telegram.

Tasks:
1. Input: abstract + first 2 chunks + last chunk
2. Gemini -> JSON: summary_en, summary_ru, tags
3. Store enrichment independently from `ingest_status`.

**Verify:** enrichment failure does not make an already indexed paper unsearchable.

---

## Phase 5: Hybrid retrieval without agent

**Goal:** precise terms and semantic matches both retrieve correct sources.

Tasks:
1. Add PostgreSQL full-text index for chunks and metadata filters.
2. Combine dense and full-text ranks with reciprocal rank fusion.
3. Implement `/list TOPIC` using hybrid retrieval.

**Verify:** exact model/term query succeeds when dense-only baseline misses it.

---

## Phase 6: Answer with citations without agent

**Goal:** `/ask` returns grounded answer instead of raw snippets.

Tasks:
1. Retrieve hybrid context with arXiv ID, title, section, and text.
2. Generate answer with mandatory `[arxiv_id]` citations.
3. Add `/summary TOPIC`: group chunks by paper, then synthesize.

**Verify:** answer cites only papers present in retrieved context and says when evidence
is insufficient.

---

## Phase 7: Synthesis routing

**Goal:** compare and multi-paper questions use broader evidence than a single top-k
retrieval.

Tasks:
1. Route point questions to direct hybrid retrieval.
2. For synthesis: decompose query, retrieve per subquestion, summarize per paper, and
   produce cited reduce answer.
3. Evaluate quality with 10-15 real questions before adding new retrieval models.

**Verify:** comparison answer covers evidence from each relevant paper rather than only
the highest-similarity chunks.

---

## Phase 8: LangGraph agent

**Goal:** free-text orchestration of existing functions.

Graph:
```
Router Groq
  find_papers  -> parse -> translate -> arxiv -> ingest_pipeline
  list_topic   -> kb_list
  summarize    -> kb_retrieve -> synthesize
  clarify      -> ask user
```

Tasks:
1. AgentState + SQLite checkpointer
2. Wire nodes to functions from phases 1-7
3. Progress updates in Telegram during long ingest

**Verify:** "find papers last month on MEV in web3" runs full pipeline.

**Learn:** agent = graph of function calls; router is a classifier.

---

## Phase 9: Backup and reliability

Tasks:
1. JSONL append after each successful ingest
2. Daily manifest: arxiv_ids + chunk counts
3. `/backup` command
4. Optional: fallback local Postgres URL if Supabase down

**Verify:** controlled row recovery from JSONL restores metadata and records required
re-index work.

---

## Phase 10+ (optional)

| Feature | When |
|---------|------|
| Semantic Scholar API | after arXiv stable |
| PDF OCR Tesseract | when empty_text failures matter |
| Langfuse tracing | when debugging agent loops |
| Colab batch reindex | when library > 500 papers |
| MCP tool servers | when many external integrations |
| map-reduce full-text summary | when abstract+sample chunks insufficient |

---

## Self-check after each phase

Answer these five questions:

1. Where is data stored? (file / Postgres / process memory)
2. Who decides next step? (Python if/else vs LLM router)
3. What goes into LLM? (abstract vs chunks vs synthesis context)
4. What happens on error? (ingest_status, retry, skip)
5. How to verify independently? (approved manual command, DB query, or test)

---

## API cost per new paper (estimate)

~50 chunks per paper:

| Step | Calls |
|------|-------|
| Summary | 1 |
| Embeddings | ~50 |
| Router | 1 per user message |

9 new papers ~ 450 embed calls. Dedupe and skip re-embed save quota.

---

## Summary strategy (confirmed)

For topic synthesis use:
- paper summaries (summary_ru / summary_en)
- top 3-5 chunks per paper from vector search

Not full paper text in one prompt. Full text stays indexed for deeper queries later.

---

## Current next step

1. Execute `specs/001-stabilize-rag-ingest/tasks.md` through T001-T017.
2. Verify lifecycle backfill and explicit reindex before enabling ready-only retrieval.
3. Add at least three papers, then complete section evaluation on five PDFs.
4. Continue to Phase 4 only after Phase 3.5 verification is recorded.
