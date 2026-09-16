---
type: Plan
title: Knowledge Runtime — plan and architecture
description: Target architecture for the research assistant as a Knowledge Runtime; execution is Spec Kit features, not this folder.
tags: [plan, roadmap, vision, architecture, knowledge-runtime]
lang: en
status: draft
generated:
  by: human:ramilmustafin
  at: 2026-09-09T00:50:00+04:00
---

# Knowledge Runtime — Plan and Architecture

> **Target design, not as-built.** As-built behavior lives in [../index.md](../index.md)
> and [../system-overview.md](../system-overview.md). Execution lives in
> [`specs/`](../../specs/) — never treat this folder as a task list.

Personal research assistant: Telegram bot, arXiv, local PDF library, PostgreSQL +
pgvector. Target: turn the search pipeline into a **Knowledge Runtime** (chunking,
hybrid retrieval, rerank, routing, corrective loops, eval). GraphRAG is late.
The indexed library has a read-only MCP server (stdio + token-gated Streamable
HTTP). MCP clients, external sources, and retrieval ACL remain out of scope.

## Documents

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Goals, constraints, stack, Spec Kit workflow |
| [02-architecture-diagrams.md](./02-architecture-diagrams.md) | Mermaid: runtime, ingest, ask, pillars |
| [03-research-assistant-blueprint.md](./03-research-assistant-blueprint.md) | Current layout, UX, ingest, retrieval modes |
| [04-database-schema.md](./04-database-schema.md) | Tables that exist or are gated by a spec |
| [05-build-roadmap.md](./05-build-roadmap.md) | Spec sequence after ingest gate |

Strategy map (Russian): [`../../RAG_UPGRADE_PLAN.md`](../../RAG_UPGRADE_PLAN.md).
Constitution: [`../../.specify/memory/constitution.md`](../../.specify/memory/constitution.md).
Feature index: [`../../specs/README.md`](../../specs/README.md).

## Current execution

Active feature: [`specs/018-mcp-http-auth/`](../../specs/018-mcp-http-auth/) (verified).

- `spec.md` — user behavior
- `plan.md` — design
- `tasks.md` — only allowed code work

Specs `001`–`018` are verified. No `app/` changes come from this vision folder.

## Key decisions

- **Deploy:** Docker Compose on local PC; cloud LLM APIs only
- **User:** single Telegram whitelist
- **DB:** Postgres + pgvector (Docker or remote). PDF on volume, not in DB
- **Languages:** Russian + English
- **Sources:** arXiv primary; full PDF download always kept
- **Retrieval today:** dense `halfvec` + Postgres FTS + RRF; ready-only `indexed`
- **Agent today:** Python modules + heuristic router, not LangGraph
- **Agent later:** planner/router as Spec `005`, after CRAG
- **Models:** Gemini embeddings; DeepSeek V3.2 generation through OpenRouter
- **Ingest:** `pending -> text_ok -> indexed | failed`
- **Recovery:** `/search` skips `indexed`; `/reindex` only incomplete rows
- **MCP:** read-only stdio + token-gated Streamable HTTP; OAuth/ACL and external sources deferred
- **Out of scope now:** multi-user ACL, Elasticsearch/Qdrant, GROBID, embedding fine-tune

## Typical scenario

```
User: find papers from last month on topic X
  -> arXiv search -> lifecycle gate -> PDF -> extract -> chunk -> embed -> indexed

User: /ask ...
  -> route point|synthesis -> hybrid retrieve -> (future rerank/CRAG) -> cited answer
```
