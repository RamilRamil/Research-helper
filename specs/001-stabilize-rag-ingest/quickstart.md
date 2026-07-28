# Quickstart: Verify Stabilize RAG Ingest

## Preconditions

- Database migration for retrieval index applied.
- At least five stored PDF papers available for section evaluation.
- Before/after state for exactly two legacy paper records is recorded.
- Credentials remain outside documentation and source control.

## Classify legacy records before retrieval rollout

1. Record `arxiv_id`, current state, chunk count, and null embedding count for both
   existing papers.
2. Apply approved lifecycle backfill.
3. Confirm each row is now `indexed` or `failed`.
4. Only then enable ready-only retrieval filtering.

## Verify duplicate avoidance

1. Run `/search <topic>` until at least one paper reaches `indexed`.
2. Run same command again.
3. Confirm existing indexed papers are reported as skipped.
4. Confirm no PDF modification time, chunk count, or embedding count changes for
   skipped papers.

## Verify explicit reindex

1. Select one `failed` and one `text_ok` paper.
2. Run `/reindex <arxiv_id>` for each.
3. Confirm operation transitions through `pending` and ends in `indexed` or a newly
   recorded `failed` state.
4. Run `/reindex <arxiv_id>` for an `indexed` paper.
5. Confirm command rejects it without changing PDF location, chunk count, or state.

## Verify concurrent ingest rejection

1. Start a long ingest for one arXiv ID via `/search` or `/reindex`.
2. While it runs, issue a second `/reindex` or ingest path for the same ID.
3. Confirm busy rejection, unchanged chunk count, and no extra embedding spend for the
   rejected attempt.

## Verify lifecycle and failure

1. Process a normal paper and confirm state path `pending -> text_ok -> indexed`.
2. Trigger a controlled ingest failure using an invalid source or a temporary
   unavailable dependency.
3. Confirm resulting state is `failed`, diagnostic is present, and any downloaded PDF
   still exists.
4. Confirm retrieval cannot return chunks belonging to failed paper.

## Verify retrieval eligibility and index

1. Place one paper in `indexed` and one in a non-ready state.
2. Run a question matching both papers.
3. Confirm result set contains only chunks from ready paper.
4. Inspect query plan for nearest-neighbor query and record whether compatible index
   is selected.

## Evaluate PDF sections

1. Ensure at least five papers exist; owner may run `/search` to add papers first.
2. Compare stored section labels with headings visible in PDF.
3. Record coverage, false positives, and missed headings in feature notes or issue.
4. Choose one outcome:
   - retain PDF-first extraction and improve regex only if errors are limited;
   - create a separate LaTeX-first feature if labels are unreliable.
