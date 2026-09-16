# Plan

- Download arXiv e-print tarball with existing `httpx`.
- If `.tex` present: strip `%` comments, join, return as extract text.
- Else: current PyMuPDF path.
- Wire `ingest_paper` extract through one function. No new deps.
