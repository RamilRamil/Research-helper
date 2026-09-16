# Database Schema

PostgreSQL + pgvector. This file matches the **intended current** model (papers + chunks
+ lifecycle + FTS). Extra tables (`research_sessions`, `chunk_feedback`, graph nodes)
are **not** as-built and must not be created until a spec + SQL script is approved.

---

## papers

One row per arXiv paper.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE papers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arxiv_id        TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    abstract        TEXT,
    authors         JSONB,
    categories      TEXT[],
    published_at    TIMESTAMPTZ,
    pdf_url         TEXT,
    pdf_local_path  TEXT,
    page_count      INTEGER,
    text_chars      INTEGER,

    summary_en      TEXT,
    summary_ru      TEXT,
    tags            TEXT[],

    ingest_status   TEXT NOT NULL DEFAULT 'pending',
    ingest_error    TEXT,

    found_by_query  TEXT,
    search_query    TEXT,
    ingested_at     TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_papers_published_at ON papers (published_at DESC);
CREATE INDEX idx_papers_tags ON papers USING GIN (tags);
CREATE INDEX idx_papers_ingest_status ON papers (ingest_status);
```

Apply via `scripts/` as already in the repo; do not duplicate blindly. Source of truth
for live columns is the applied SQL, not this vision file.

---

## chunks

```sql
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id        UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    section         TEXT,
    text            TEXT NOT NULL,
    token_count     INTEGER,
    text_hash       TEXT,
    embedding       halfvec(3072),
    text_search     tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (paper_id, chunk_index)
);

CREATE INDEX idx_chunks_paper_id ON chunks (paper_id);
CREATE INDEX idx_chunks_text_search ON chunks USING GIN (text_search);
-- HNSW: only after query operator matches stored type (001)
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding halfvec_cosine_ops);
```

Dimension and type must match `gemini-embedding-001` usage in `embedder.py` / `search.py`
(`halfvec(3072)`, `<=>`). If live SQL still uses `vector` not `halfvec`, 001 owns the
alignment — do not "fix" from this document.

---

## Ingest lifecycle

```text
pending -> text_ok -> indexed
pending -> failed
text_ok -> failed
failed|text_ok|pending -> pending (explicit /reindex only)
```

Retrieval: `p.ingest_status = 'indexed'` and `c.embedding IS NOT NULL`.

Legacy backfill (001): chunks complete with no null embedding -> `indexed`; else `failed`
with recovery hint. PDF path unchanged.

---

## Gated (do not create now)

| Object | When |
|--------|------|
| `source_type` / `latex_local_path` on papers | LaTeX ingest spec if section eval fails |
| Graph / community / entity tables | spec `007` |
| ACL columns on chunks/papers | multi-user decision |
| `research_sessions` | only if a spec needs audit |
| `chunk_feedback` | eval spec `006` if thumbs become a requirement |

---

## Example queries

Dedupe:

```sql
SELECT id, ingest_status FROM papers WHERE arxiv_id = $1;
```

Hybrid is application-side RRF over two SQL legs (dense `<=>` and `text_search @@
plainto_tsquery('english', $q)`), both filtered to `indexed`. See `app/db/search.py`.
