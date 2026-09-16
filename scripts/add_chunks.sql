-- Base chunks table. Full-text (chunks_fts.sql) and the halfvec conversion +
-- HNSW index (embedding_halfvec_hnsw.sql) are applied as separate follow-ups;
-- HNSW needs halfvec, so it cannot live here where embedding is still vector(3072).
CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id        UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    text            TEXT NOT NULL,
    text_hash       TEXT,
    token_count     INTEGER,
    embedding       vector(3072),
    created_at      TIMESTAMPTZ DEFAULT now(),
    section         TEXT,
    chunk_gen       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (paper_id, chunk_gen, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_paper_id ON chunks(paper_id);
