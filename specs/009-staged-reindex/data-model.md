# Data model

- `papers.chunk_gen` INTEGER NOT NULL DEFAULT 0 — live generation.
- `chunks.chunk_gen` INTEGER NOT NULL DEFAULT 0.
- Unique `(paper_id, chunk_gen, chunk_index)`.
