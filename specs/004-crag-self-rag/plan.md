# Implementation Plan: CRAG Self-RAG

## Design

`app/rag/crag.py`:

- `grade_support(question, hits) -> bool` JSON `{"sufficient": true|false}`
- `rewrite_query(question) -> str` JSON `{"query": "..."}` English search query
- `retrieve_with_correction(question) -> list[dict]`:
  1. `retrieve_for_ask`
  2. if empty, return []
  3. if grade true, return hits
  4. rewrite once, `retrieve_for_ask(rewrite)`
  5. if empty, return []
  6. grade original question vs new hits; true => return; else return []
- `is_grounded(question, answer, hits) -> bool`

`cmd_ask` point: `retrieve_with_correction`; empty =>
`Indexed library cannot support this question.`
Then `generate_answer`; if not `is_grounded`, send
`Answer failed groundedness check.` do not send draft.

Synthesis: after `rerank_hits`, same grade+one rewrite of original question
then retrieve_for_ask on rewrite and replace ranked if better; if still false,
return insufficient string, [].

No web. No snippet dump change required for ungrounded (new branch). Leave
existing generate-exception snippet path (pre-004).

## Files

`app/rag/crag.py`, `app/bot/main.py`, `app/rag/synthesis.py`
