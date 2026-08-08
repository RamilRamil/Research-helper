# Changelog

Chronological history for the `docs/` OKF bundle, newest first (OKF v0.2 reserved `log.md`).

## 2026-08-08 — Tier-1 concepts + diagrams

- **Added** the Tier-1 as-built concepts (EN + RU): [ingest-pipeline](ingest-pipeline.md),
  [retrieval](retrieval.md), [database](database.md). They document ingest orchestration + the
  recoverable lifecycle, hybrid retrieval + `/ask` routing + synthesis, and the live schema in
  `scripts/*.sql`.
- **Added** the [diagrams/](diagrams/README.md) sub-bundle (EN + RU): `ingest-flow` (sequence),
  `ask-flow` (flow), `paper-lifecycle` (state).
- **Flagged** in [database.md](database.md) a real defect: [scripts/add_chunks.sql](../scripts/add_chunks.sql)
  is corrupted (missing `CREATE TABLE chunks` header, HNSW index pasted over it) and cannot
  provision the schema from scratch, though the live table is correct.
- **Updated** [index.md](index.md) (+ ru): promoted the three concepts + diagrams from planned to
  present; remaining planned = `enrichment`, `bot-commands`, `configuration`.

## 2026-08-08 — OKF adoption

- **Adopted OKF v0.2** for `docs/`: bundle-root [index.md](index.md) (+ [ru](index.ru.md))
  declaring `okf_version: "0.2"`, this `log.md`, and the bilingual EN/RU convention. Provenance
  seeded via `generated.by`/`at` (agent-drafted, `status: draft`, not yet `verified`).
- **Added** [system-overview.md](system-overview.md) (+ [ru](system-overview.ru.md)) — the first
  as-built concept: the bot's layers (`bot` / `tools` / `rag` / `db`), the `/search` → `/ask`
  data flow, a Mermaid module map, and the explicit wired-vs-vision boundary (LangGraph, FastAPI,
  Groq, MCP, and extra tables are **not** wired).
- **Marked** [plan/README.md](plan/README.md) as forward-looking vision (frontmatter +
  banner) to separate the roadmap/design docs from the as-built bundle. Per-file frontmatter for
  `plan/01`–`plan/05` is still pending.
