# Research Agent - Plan and Architecture

Personal research assistant: Telegram bot, arXiv search, local PDF library, RAG, and
optional LangGraph orchestration.

## Documents

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Goals, constraints, tech stack summary |
| [02-architecture-diagrams.md](./02-architecture-diagrams.md) | Mermaid diagrams (layers, flows, LangGraph) |
| [03-research-assistant-blueprint.md](./03-research-assistant-blueprint.md) | Project structure, Telegram UX, arXiv pipeline |
| [04-database-schema.md](./04-database-schema.md) | SQL tables: papers, chunks, sessions |
| [05-build-roadmap.md](./05-build-roadmap.md) | Phased manual build guide (PDF-first) |

## Current implementation phase

Current work is specified in
[`specs/001-stabilize-rag-ingest/`](../../specs/001-stabilize-rag-ingest/):

- `spec.md` defines expected user behavior;
- `plan.md` defines lifecycle, legacy backfill, and retrieval design;
- `tasks.md` is execution order.

Manual development uses Ask-mode agent support for inspection and design. Code changes
remain deliberate, small, and verified against the active Spec Kit task.

## Key decisions

- **Deploy:** Docker Compose on local PC (24/7), cloud LLM APIs only
- **User:** single Telegram user (whitelist)
- **DB:** Supabase Postgres + pgvector, local JSONL backup + PDF volume
- **Languages:** Russian + English
- **Sources:** arXiv primary; full PDF download and text indexing
- **Agent:** one LangGraph agent with model routing (not multi-agent crew)
- **Budget:** free tiers (Gemini, Groq, Supabase, DuckDuckGo/Tavily)
- **Ingest state:** `pending -> text_ok -> indexed | failed`
- **Recovery:** normal search skips `indexed`; `/reindex <arxiv_id>` is reserved for
  incomplete records and never replaces a working index

## Typical scenario

```
User: "find papers from the last month on MEV in web3"
  -> arXiv search -> dedupe -> download PDF -> extract -> chunk -> embed
  -> summaries RU/EN -> save to DB -> reply with list

User: "summary on MEV" / "everything I have on MEV"
  -> retrieve from KB -> list or synthesis with citations
```
