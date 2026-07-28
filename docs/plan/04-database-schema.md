# Database Schema

PostgreSQL with pgvector extension.

---

## papers

One row per arXiv paper.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE papers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    arxiv_id        TEXT UNIQUE NOT NULL,       -- e.g. "2406.01234"
    title           TEXT NOT NULL,
    abstract        TEXT,
    authors         JSONB,
    categories      TEXT[],
    published_at    TIMESTAMPTZ,
    pdf_url         TEXT,
    pdf_local_path  TEXT,                       -- data/papers/{arxiv_id}.pdf
    page_count      INTEGER,
    text_chars      INTEGER,

    summary_en      TEXT,
    summary_ru      TEXT,
    tags            TEXT[],

    ingest_status   TEXT NOT NULL DEFAULT 'pending',
    -- pending | text_ok | indexed | failed
    ingest_error    TEXT,

    found_by_query  TEXT,                       -- original user message
    search_query    TEXT,                       -- normalized arXiv query
    ingested_at     TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_papers_published_at ON papers (published_at DESC);
CREATE INDEX idx_papers_tags ON papers USING GIN (tags);
CREATE INDEX idx_papers_ingest_status ON papers (ingest_status);
```

Note: paper-level embedding optional; primary search via chunks.

---

## chunks

Text segments for RAG and topic summaries.

```sql
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id        UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    section         TEXT,                       -- best-effort: Introduction, etc.
    text            TEXT NOT NULL,
    token_count     INTEGER,
    text_hash       TEXT,                       -- future content-change comparison
    embedding       vector(3072),

    created_at      TIMESTAMPTZ DEFAULT now(),

    UNIQUE (paper_id, chunk_index)
);

CREATE INDEX idx_chunks_paper_id ON chunks (paper_id);

-- HNSW index (pgvector 0.5+); adjust lists for IVFFlat if preferred
CREATE INDEX idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);
```

Embedding dimension must match active embedding model. Current implementation uses
`gemini-embedding-001` with 3072 dimensions.

## Ingest lifecycle

```text
pending -> text_ok -> indexed
pending -> failed
text_ok -> failed
failed|text_ok|pending -> pending (explicit /reindex only)
```

`indexed` papers are eligible for retrieval and immutable during normal search.
Before adding a ready-only retrieval filter, classify legacy `text_ok` rows:

- at least one chunk and no null embedding -> `indexed`;
- no chunks or any null embedding -> `failed` with recovery instruction.

The local PDF path remains unchanged during classification or failure.

---

## research_sessions

Optional audit log of search requests.

```sql
CREATE TABLE research_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL,
    raw_request     TEXT NOT NULL,
    parsed_topic    TEXT,
    date_from       DATE,
    date_to         DATE,
    papers_found    INTEGER DEFAULT 0,
    papers_new      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## chunk_feedback (optional, phase 2)

For improving retrieval quality.

```sql
CREATE TABLE chunk_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id        UUID REFERENCES chunks(id) ON DELETE CASCADE,
    user_id         BIGINT NOT NULL,
    rating          SMALLINT,                   -- 1 = good, -1 = bad
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## Example queries

### Dedupe check

```sql
SELECT id, ingest_status FROM papers WHERE arxiv_id = $1;
```

### List by topic keyword

```sql
SELECT arxiv_id, title, summary_ru, published_at, pdf_url
FROM papers
WHERE ingest_status = 'indexed'
  AND (
    'MEV' = ANY(tags)
    OR title ILIKE '%MEV%'
    OR abstract ILIKE '%MEV%'
  )
ORDER BY published_at DESC;
```

### Vector search (pseudo-SQL)

```sql
SELECT c.paper_id, c.text, p.arxiv_id, p.title,
       1 - (c.embedding <=> $query_embedding) AS score
FROM chunks c
JOIN papers p ON p.id = c.paper_id
WHERE p.ingest_status = 'indexed'
ORDER BY c.embedding <=> $query_embedding
LIMIT 30;
```

---

## JSONL backup record format

One line per successfully indexed paper:

```json
{
  "arxiv_id": "2406.01234",
  "title": "...",
  "summary_en": "...",
  "summary_ru": "...",
  "tags": ["MEV", "ethereum"],
  "pdf_local_path": "data/papers/2406.01234.pdf",
  "chunk_count": 42,
  "ingested_at": "2026-07-03T10:00:00Z"
}
```

Vectors not included in JSONL (re-embed from PDF/text if restore needed).
