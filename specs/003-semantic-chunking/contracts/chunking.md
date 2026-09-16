# Contract: chunk_text

`chunk_text(text) -> list[dict]` with keys `text`, `section`.

- Empty/whitespace sections omitted.
- `len(text) <= CHUNK_SIZE` except a single unsplittable unit.
- No mid-word cut except that unsplittable unit case.
- `save_chunks` unchanged: still `DELETE` then insert for the paper being
  ingested/reindexed only.
