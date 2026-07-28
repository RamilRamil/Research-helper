# Overview

## Agent capabilities (target)

| Layer | Purpose | Chosen approach |
|-------|---------|-----------------|
| Perception & input | Text, documents, Telegram | aiogram 3, PyMuPDF, trafilatura |
| Memory & knowledge | Session + long-term KB | pgvector; LangGraph checkpoint only after agent phase |
| Planning | Multi-step research | Plain Python first; LangGraph later |
| Actions & tools | arXiv, PDF, RAG | Python tools, optional MCP later |
| Feedback & learning | Improve over time | Thumbs up/down, eval set, RAG updates (no fine-tune at start) |
| Orchestration | Reliable runtime | LangGraph + Docker Compose |
| Safety | Personal bot guardrails | user_id whitelist, rate limits, SSRF protection on URLs |

## Constraints (confirmed)

| Parameter | Value |
|-----------|-------|
| Domain | Research assistant |
| Deploy | Docker locally (weak hardware OK for LLM) |
| LLM | Cloud free tiers (Gemini, Groq) |
| Colab/Kaggle | Batch jobs only (reindex, heavy reports), not 24/7 hosting |
| Stack language | Python |
| Integrations | Telegram, PostgreSQL + pgvector |
| Real-time | Not required for MVP (async Telegram is enough) |
| Users | Personal (single whitelist) |
| Data | Supabase OK + local duplication (JSONL + PDF volume) |
| Languages | Russian + English |
| Content | Full PDF download and text indexing |
| Development workflow | Manual implementation with Ask-mode agent support |

## Recommended stack

```
Frontend/channel:  Telegram (aiogram 3)
Backend:           Python bot polling; optional FastAPI health later
Agent core:        Plain Python functions; LangGraph only after retrieval is stable
LLM routing:       Gemini for embeddings; generation/router introduced in later phases
Embeddings:        Gemini gemini-embedding-001 (3072 dimensions)
Search:            arXiv API (primary), duckduckgo-search / Tavily (optional later)
Documents:         PyMuPDF (PDF), trafilatura (HTML)
Database:          PostgreSQL + pgvector (Supabase free or Docker)
Session memory:    LangGraph SQLite checkpointer
Observability:     Langfuse cloud free (optional, phase 2)
Safety:            whitelist, rate limits, URL fetch guards
Backup:            JSONL delta export + PDF files on Docker volume
Batch:             Colab notebook for reindex (optional)
```

## What NOT to build first

- Custom orchestrator from scratch
- Fine-tuning before eval dataset exists
- GraphRAG before simple vector RAG works
- Multi-agent crews before single agent is stable
- Full PDF OCR (skip scanned PDFs initially)
- Semantic Scholar / Google Scholar (after arXiv pipeline is stable)

## Free tier notes

- **Gemini free:** main cost driver for summaries + embeddings; dedupe saves quota
- **Groq free:** routing and short steps
- **Supabase free:** ~500 MB; store text chunks, not PDF binaries
- **arXiv API:** free, no key; respect 3s delay between bulk requests
- **Colab/Kaggle:** not for bot hosting (sessions timeout)

Typical bottleneck: RPM limits and embedding volume per paper (~30-80 chunks), not money.

## Delivery rule

`indexed` means all chunks are embedded and eligible for retrieval. Summaries, tags,
and future enrichments are not prerequisites for this state. Normal search skips an
`indexed` paper; recovery of `pending`, `text_ok`, or `failed` paper is explicit.
