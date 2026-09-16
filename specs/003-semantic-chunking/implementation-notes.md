# Implementation notes: 003-semantic-chunking

**Date:** 2026-09-09

Replaced char window with paragraph/sentence pack in `chunker.py`.
`indexed` papers unchanged until `/reindex` (incomplete only).

Dry-run app image, PDF `2604.16548` (15 pages): 90 chunks, 0 over cap,
mid-alnum chunk-end rate 0.078 (SC-001 80% boundary target met).

Live 2026-09-09 13:08: `/reindex 2607.20124` -> `indexed ok + enriched`.
Previously this id was `failed` (85 chunks, all null embeddings). New chunker
used on explicit reindex only.
