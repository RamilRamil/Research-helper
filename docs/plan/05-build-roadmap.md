# Build Roadmap

Bottom-up. Spec Kit is the execution mechanism. Phases 0–3 in the old calendar sense
are largely **done** in code. Do not rebuild the skeleton.

---

## Gate: Spec 001 — Stabilize ingest

**Folder:** [`specs/001-stabilize-rag-ingest/`](../../specs/001-stabilize-rag-ingest/)

**Goal:** repeated discovery is idempotent; incomplete papers recoverable; retrieval
never sees non-`indexed` rows.

Tasks live only in `tasks.md` (T001–T017 and any remaining items there).

**Verify (2026-09-09 notes):** backfill applied (no-op); ready-only counts recorded;
advisory lock busy without mutation; HNSW index eligible on `halfvec` `<=>`;
five-PDF section eval = retain PDF-first; T011 repeat `/search memory injection`
shows two `(indexed)` and eight new metadata rows.

**Stop:** 001 verify recorded. Next feature is spec `002` rerank only, after owner
says specify.

---

## Already in the tree (not a rebuild)

Treat as baseline, not as "Phase 5 still missing":

- Section window chunking
- Dense retrieval + FTS + RRF
- `/ask` grounded generate + heuristic synthesis route
- Paper enrichment independent of `indexed` (if commands exist — see bot docs)

If behavior drifts from docs, fix docs or file a spec — do not silently add a second path.

---

## After 001 — one spec at a time

| Order | Spec intent | Pillar | Verify idea |
|-------|-------------|--------|-------------|
| 002 | Two-stage retrieve: hybrid fetch_k then rerank to small context | 3 | Same questions: less junk in cited context |
| 003 | Semantic / adaptive chunking (MCPD or approved alternative); optional LaTeX-first if 5-PDF section eval fails | 1 | Coreference held inside chunks; reindex policy explicit |
| 004 | CRAG-style retrieval grade + Self-RAG groundedness | 6 | Empty/noisy KB does not hallucinate |
| 005 | Planner + tool router (vector / FTS / synthesis); not LangGraph-first | 5 | Simple ask stays cheap; compare-questions cover multiple papers |
| 006 | Systematic eval (Ragas or approved equivalent) + traces | 8 | CI or checklist catches retrieval vs generation failure |
| 007 | GraphRAG (entities, Leiden communities, community summaries) | 4 | Multi-hop / corpus question that hybrid misses |

Library installs for 002/003/006/007 need a separate yes.

---

## Explicitly later / never from this roadmap

| Item | Rule |
|------|------|
| Retrieval ACL | Deferred |
| Local read-only MCP | Built in `017` |
| MCP Streamable HTTP + token | Built in `018` |
| MCP OAuth / ACL / external sources | Separate future feature |
| LangGraph wrapping existing functions | Only if 005 chooses it in plan.md |
| SPECTER2 / extra dense model | Only if 002 eval shows ranking failure after rerank options |
| GROBID, ES, Qdrant | No |
| Embedding fine-tune | No eval set |

---

## Self-check before closing a spec

1. Where is data? (PDF file / Postgres / RAM)
2. Who chooses next step? (Python vs LLM planner)
3. What enters the LLM? (ranked chunks only)
4. Failure? (`ingest_status`, no secret in `ingest_error`)
5. How to verify without vibes?

---

## Quota reminder

~50 embed calls per new paper. Dedupe and skip `indexed` save the budget. Rerank and
planner add more calls — justify in that spec's plan.

---

## Current next step

1. Spec Kit `002` rerank only — owner command to specify.
2. Do not implement 002 from this roadmap file.
