# Internal Contract: Ingest and Retrieval Lifecycle

## `save_paper(paper, topic, search_query) -> bool`

Returns `true` only when metadata created a new paper row.

Normal search caller contract:

- `true`: paper is eligible for ingest.
- `false` with state `indexed`: report as skipped; do not call ingest.
- `false` with state `pending`, `text_ok`, or `failed`: do not silently replace data;
  report state and require explicit `/reindex`.

## `/reindex <arxiv_id>`

Authorization contract:

- existing Telegram whitelist remains required.

State contract:

- `pending`, `text_ok`, or `failed`: transition to `pending`, then run ingest;
- `indexed`: reject without mutating PDF, chunks, embeddings, or lifecycle state;
- unknown `arxiv_id`: report not found without creating a paper.

Concurrency contract:

- acquire per-paper advisory lock before ingest work;
- if lock is held: report busy, make no mutations, leave state unchanged.

Failure contract:

- retain existing PDF;
- record `failed` plus safe diagnostic;
- never make a failed reindex of an incomplete paper appear `indexed`.

## `reindex_paper(arxiv_id) -> str`

Must acquire the per-paper advisory lock **before** any lifecycle mutation.
If lock is not acquired: raise busy, leave all rows unchanged.
If paper is `indexed` or missing: raise `ValueError`, no chunk/PDF mutation.
Otherwise: `prepare_reindex` then the same ingest body as `ingest_paper`.

## `ingest_paper(arxiv_id) -> str`

Success contract:

- PDF exists at `pdf_local_path`.
- every stored chunk has an embedding;
- parent paper state is `indexed`;
- parent `ingest_error` is empty.

Concurrency contract:

- callers that mutate paper content MUST hold the per-paper advisory lock for the
  duration of download/extract/chunk/embed finalization.

Failure contract:

- function raises the original failure for command-level reporting;
- caller persists parent state `failed` and a safe diagnostic message;
- successfully stored PDF is not deleted.

## `search_chunks(query, limit) -> list[dict]`

Eligibility contract:

- return chunks only from papers with state `indexed`;
- return only chunks with an embedding;
- preserve `arxiv_id`, title, section, text snippet, and distance for source display.

Performance contract:

- nearest-neighbor ordering must have a compatible approximate-nearest-neighbor index
  once the corresponding migration is applied.
