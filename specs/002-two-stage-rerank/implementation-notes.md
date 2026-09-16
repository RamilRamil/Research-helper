# Implementation notes: 002-two-stage-rerank

**Date:** 2026-09-09

T001-T005: `app/rag/rerank.py`, point `/ask` via `retrieve_for_ask`, synthesis
reranks merged unique hits (`keep=12`) before map.

T006 live `/ask` (2026-09-09 12:01, after model fallback + rebuild):

- Query: `memory injection`, route `point`.
- Answer returned (not 503). Sources: one paper `2607.05189`.
- In-body cites used `[1][2][3][4]` (context row numbers), not `[arxiv_id]`.
  Prompt asks for arxiv_id; generation still used indices. Out of 002 scope
  unless owner wants a follow-up prompt tweak.
