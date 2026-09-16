# Implementation notes: 004-crag-self-rag

Code: `app/rag/crag.py`. Point `/ask` uses retrieve_with_correction + is_grounded.
Synthesis grades merged pool; one rewrite then retrieve_for_ask.

No web. Bot rebuilt 2026-09-09.
