# Overview

## Target: Knowledge Runtime

A production RAG stack is not "embed + top-k + LLM". It is a runtime that keeps
related facts in coherent chunks, retrieves with complementary signals, reranks
before generation, routes hard questions, refuses ungrounded claims, and measures
quality independently of vibes.

| Pillar | Role | Near-term |
|--------|------|-----------|
| Semantic / adaptive chunking | Keep coreference and local context | After 001; breaks index |
| Hybrid search | Dense semantics + sparse exact terms | **As-built** (RRF) |
| Two-stage + rerank | Wide recall, then precise context | Next spec after 001 |
| Knowledge graph / GraphRAG | Multi-hop and corpus-level questions | Late |
| Agentic planner / router | Decompose + pick retrieval tool | After corrective loops |
| CRAG / Self-RAG | Retrieval quality gate + groundedness | After rerank |
| Retrieval-native ACL | Filter in the index, not after generate | Deferred (single user) |
| Eval + observability | Precision/recall/faithfulness/relevancy + traces | Cross-cutting after 002 |

## Constraints (confirmed)

| Parameter | Value |
|-----------|-------|
| Domain | Personal research assistant |
| Deploy | Docker locally |
| LLM / embeddings | DeepSeek V3.2 chat; Gemini embeddings |
| Stack language | Python |
| Channel | Telegram (aiogram) |
| Store | PostgreSQL + pgvector; local PDF volume |
| Users | One whitelist id |
| Languages | Russian + English |
| Content | Full PDF download and text index |
| Development | Spec Kit feature folders; no code without `tasks.md` |
| New libraries | Explicit approval before install |
| MCP | Read-only stdio + token-gated Streamable HTTP; OAuth/ACL deferred |
| ACL in index | Deferred |

## Recommended stack (current, not future rewrite)

```
Channel:     Telegram (aiogram)
Runtime:     Python bot polling
LLM:         DeepSeek V3.2 generate; Gemini embed
Vectors:     pgvector halfvec(3072), cosine
Sparse:      Postgres tsvector / ts_rank (english)
Fusion:      Reciprocal Rank Fusion in app/db/search.py
Docs:        PyMuPDF; PDF files retained on failure
Orchestration: Python call graph; LangGraph not a prerequisite
Observability: none yet (pillar 8)
Safety:      ALLOWED_USER_ID whitelist; no retrieval ACL
```

Do not migrate to FastAPI + SQLAlchemy + Alembic + LangGraph as a "target tree"
before retrieval pillars 3/6/5 are specified. Keep `psycopg` + `scripts/*.sql`.

## What NOT to build first

- GraphRAG before ingest + hybrid + rerank are stable
- Multi-agent crews
- Custom orchestrator
- Fine-tuning without an eval set
- Full PDF OCR (skip scanned PDFs)
- Semantic Scholar / Google Scholar
- MCP servers for LMS/files/DBs
- Second live database with bidirectional sync

## Free tier notes

- Gemini quota is the bottleneck (embeddings per paper, then generate).
- Skip `indexed` papers on `/search` to save quota.
- arXiv: no key; respect delay between bulk requests.
- Store chunks in Postgres; PDFs on disk.

## Delivery rule

`indexed` means all chunks embedded and eligible for retrieval. Summaries and tags
are not required for that state. Normal search never mutates `indexed`. Incomplete
papers recover only via explicit `/reindex`.
