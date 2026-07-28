-- Convert stored embeddings to halfvec (no re-embed needed)
ALTER TABLE chunks
    ALTER COLUMN embedding TYPE halfvec(3072)
    USING embedding::halfvec(3072);

-- HNSW for cosine distance on halfvec
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks
    USING hnsw (embedding halfvec_cosine_ops);