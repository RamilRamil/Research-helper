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