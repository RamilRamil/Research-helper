# Plan

Graph retrieve still hops via `community_id`. Ranked paper chunks are
the only context for theme generate. Community summaries stay on
`/communities`, not prepended into `/ask` hits.

Theme prompt: every bullet must be supported by a passage in context;
no library-wide survey voice.

Eval `_contexts`: pass the same `text`/`snippet` the answerer formatted,
not a shorter slice.

Verify: `docker compose run` `scripts/eval_ragas.py`. Compare
`data/papers/_ragas_eval.json` to the 0.23 / ~1.00 graph row.
