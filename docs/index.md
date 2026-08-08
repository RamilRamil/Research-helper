---
type: Reference
title: Research Helper documentation
description: OKF knowledge bundle for the Research Helper Telegram bot — arXiv ingest, RAG retrieval, and grounded answering as wired today.
okf_version: "0.2"
tags: [index, documentation, research-helper]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
---

# Research Helper documentation

🇷🇺 [Русская версия](index.ru.md)

This directory is an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(OKF v0.2) bundle: every concept is a Markdown file with YAML frontmatter, versioned in git
alongside the code it describes. Change history is in [log.md](log.md).

**As-built, not aspirational.** These docs describe **what is actually wired up and running
today** — the aiogram bot, the plain-Python RAG functions, Gemini, and Postgres. Forward-looking
design (LangGraph, FastAPI, an MCP server, extra tables) lives in [plan/](plan/README.md) and is
labelled as vision, not reality. A doc that lies about what is connected is worse than no doc.

**Bilingual convention.** Each concept has an English base file (`name.md`) and a Russian
sibling (`name.ru.md`), cross-linked at the top and carrying `lang: en` / `lang: ru`. Keep the
pair in sync when the wiring changes.

**Provenance.** `generated.by` follows the OKF actor convention: `human:<id>` for
human-authored content, `<producer>/<model>` for agent-drafted content. Agent-drafted docs
(`research-helper/claude-opus-4.8`) are `status: draft` and have not yet been human-`verified`;
add a `verified` entry after review.

## Concepts (as-built)

- [system-overview.md](system-overview.md) · [🇷🇺](system-overview.ru.md) — the whole bot:
  layers (`bot` / `tools` / `rag` / `db`), the data flow from `/search` to `/ask`, and the
  wired-vs-vision boundary.
- [ingest-pipeline.md](ingest-pipeline.md) · [🇷🇺](ingest-pipeline.ru.md) — `/search` → save
  metadata → advisory lock → download → extract → chunk → embed → `indexed`; the recoverable
  lifecycle and `/reindex`.
- [retrieval.md](retrieval.md) · [🇷🇺](retrieval.ru.md) — hybrid search (dense `halfvec` + Postgres
  full-text + RRF), ready-only filtering, `/ask` routing (point vs synthesis), grounded answers,
  and map-reduce synthesis.
- [database.md](database.md) · [🇷🇺](database.ru.md) — the schema as it exists in `scripts/*.sql`
  (`papers`, `chunks`, `halfvec`, `text_search`, HNSW), the lifecycle backfill, and a known-broken
  migration.

## Diagrams

- [diagrams/README.md](diagrams/README.md) · [🇷🇺](diagrams/README.ru.md) — the Mermaid sub-bundle:
  [ingest-flow](diagrams/ingest-flow.md), [ask-flow](diagrams/ask-flow.md), and
  [paper-lifecycle](diagrams/paper-lifecycle.md). (The module map lives in
  [system-overview.md](system-overview.md).)

## Planned additions (not yet written)

Intended Tier-2 concepts; they do not exist yet and are listed so the bundle's target shape is
explicit.

- `enrichment.md` — `summary_en` / `summary_ru` / `tags`, independent of `ingest_status`.
- `bot-commands.md` — operator reference for `/start /search /ask /list /enrich /reindex` and
  the inline ingest buttons.
- `configuration.md` — environment variables, `docker-compose`, `.env`.

## Related (outside this bundle)

- [../README.md](../README.md) — project overview, setup, and bot commands.
- [plan/README.md](plan/README.md) — forward-looking design & roadmap (LangGraph, hybrid
  retrieval phases, MCP). Labelled vision; not all of it is built.
- [../specs/001-stabilize-rag-ingest/](../specs/001-stabilize-rag-ingest/spec.md) — the active
  Spec Kit feature (ingest lifecycle stabilization).
