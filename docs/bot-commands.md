---
type: Reference
title: Bot commands — operator reference
description: The Telegram command surface — /start /search /ask /list /enrich /reindex /communities, inline ingest buttons, and admin/reader role gate.
tags: [telegram, commands, operator, reference]
lang: en
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/bot/main.py
    title: command + callback handlers
---

# Bot commands — operator reference

🇷🇺 [Русская версия](bot-commands.ru.md)

Every handler checks `app/bot/auth.py` against `ALLOWED_USERS` (or legacy `ALLOWED_USER_ID`).
Unknown users get "You are not allowed to use this bot". Allowlisted users without the required
role get "You are not allowed to use this command".

| Command | Roles | What it does |
|---|---|---|
| `/start` | admin, reader | Access check + greeting. |
| `/search <topic>` | admin | arXiv search (last 365 days, up to 10), saves new rows as `pending`, replies with a list and per-paper ingest buttons. |
| `/ask <question>` | admin, reader | Routed answer (point / synthesis / graph) with a cited **Sources** block. See [retrieval.md](retrieval.md). |
| `/list <topic>` | admin, reader | `hybrid_search` over the indexed library, deduped to the top 10 papers (no generation). |
| `/enrich <arxiv_id>` | admin | (Re)generate the RU/EN summary + tags card. Requires the paper to be in the DB. See [enrichment.md](enrichment.md). |
| `/reindex <arxiv_id>` | admin | Recover incomplete ingest, or staged-rebuild an already `indexed` paper (old chunks stay searchable until swap). `/reindex indexed` rebuilds all indexed papers one by one. |
| `/communities` | admin | Rebuild Leiden communities on indexed papers (shared tag or category). Graph `/ask` expands to the same community. |
| any other text | admin, reader | Echoed back. |
| ingest callbacks (`add:` / `addall`) | admin | Inline buttons from `/search`. |

## Inline ingest buttons

`/search` renders an inline keyboard:

- **`Add {id}`** (callback `add:{id}`) — ingest that one paper via `_ingest_one` (skips if already
  `indexed`), then auto-enrich. `Indexed {id}` is shown instead when it is already indexed.
- **`Add all (not indexed)`** (callback `addall`) — ingest every paper from the caller's last
  `/search` result, sequentially.

The full ingest sequence behind a button is in
[diagrams/ingest-flow.md](diagrams/ingest-flow.md).

## Notes

- `/search` **only saves metadata** (`pending`); PDFs are downloaded and embedded when a button is
  tapped, not during search.
- Long replies are truncated to Telegram's limits (answers and snippet fallbacks are capped near
  4000 chars).
- The last `/search` id set is held **in process memory** per user (`_last_search`) — it does not
  survive a bot restart, so `Add all` needs a fresh search after a restart.
