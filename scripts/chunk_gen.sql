ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS chunk_gen INTEGER NOT NULL DEFAULT 0;

ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS chunk_gen INTEGER NOT NULL DEFAULT 0;

ALTER TABLE chunks
    DROP CONSTRAINT IF EXISTS chunks_paper_id_chunk_index_key;

CREATE UNIQUE INDEX IF NOT EXISTS chunks_paper_gen_index
    ON chunks (paper_id, chunk_gen, chunk_index);
