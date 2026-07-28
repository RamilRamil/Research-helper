CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks
    USING hnsw (embedding halfvec_cosine_ops); (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id        UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    text            TEXT NOT NULL,
    text_hash       TEXT,
    token_count     INTEGER,
    embedding       vector(3072),
    created_at      TIMESTAMPTZ DEFAULT now(),
    section         TEXT,
    UNIQUE(paper_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_paper_id ON chunks(paper_id);