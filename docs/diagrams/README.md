---
type: Reference
title: Diagrams index
description: Mermaid flow and state diagrams reflecting what is wired today; bilingual EN/RU.
tags: [index, diagrams]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
---

# Diagrams

🇷🇺 [Русская версия](README.ru.md)

Flow and state diagrams for Research Helper, reflecting **what is actually wired up today**.
Mermaid source, renders in GitHub / VS Code / most Markdown viewers. The **module map** lives in
[../system-overview.md](../system-overview.md); this sub-bundle holds the flow/state diagrams.

- [ingest-flow.md](ingest-flow.md) · [🇷🇺](ingest-flow.ru.md) — one paper from `Add` button to
  `indexed`: advisory lock, download, extract, chunk, embed, auto-enrich. Pairs with
  [../ingest-pipeline.md](../ingest-pipeline.md).
- [ask-flow.md](ask-flow.md) · [🇷🇺](ask-flow.ru.md) — `/ask` routed into point vs synthesis, plus
  the snippet fallback. Pairs with [../retrieval.md](../retrieval.md).
- [paper-lifecycle.md](paper-lifecycle.md) · [🇷🇺](paper-lifecycle.ru.md) — the `ingest_status`
  state machine and the legacy backfill.

Update these when the wiring changes — a diagram that lies about what is connected is worse than no
diagram.
