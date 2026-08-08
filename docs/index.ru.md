---
type: Reference
title: Документация Research Helper
description: OKF-бандл знаний по Telegram-боту Research Helper — ingest статей с arXiv, RAG-поиск и обоснованные ответы, как собрано сегодня.
okf_version: "0.2"
tags: [index, documentation, research-helper]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
---

# Документация Research Helper

🇬🇧 [English version](index.md)

Этот каталог — бандл [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(OKF v0.2): каждый концепт это Markdown-файл с YAML-frontmatter, версионируется в git рядом с
кодом, который он описывает. История изменений — в [log.md](log.md).

**As-built, не желаемое.** Доки описывают **что реально подключено и работает сегодня** —
aiogram-бот, обычные Python-функции RAG, Gemini и Postgres. Проектное видение (LangGraph,
FastAPI, MCP-сервер, дополнительные таблицы) живёт в [plan/](plan/README.md) и помечено как
vision, не как реальность. Док, который врёт про то, что связано, — хуже, чем его отсутствие.

**Билингвальная конвенция.** У каждого концепта есть английский базовый файл (`name.md`) и
русский сиблинг (`name.ru.md`), кросс-линкованные сверху, с `lang: en` / `lang: ru`. Держи
пару в синхроне при изменении проводки.

**Provenance.** `generated.by` следует OKF-конвенции акторов: `human:<id>` для контента,
написанного человеком, `<producer>/<model>` для черновиков агента. Агентские черновики
(`research-helper/claude-opus-4.8`) имеют `status: draft` и ещё не `verified` человеком;
после ревью добавляется запись `verified`.

## Концепты (as-built)

- [system-overview.ru.md](system-overview.ru.md) · [🇬🇧](system-overview.md) — весь бот:
  слои (`bot` / `tools` / `rag` / `db`), поток данных от `/search` до `/ask` и граница
  wired-vs-vision.
- [ingest-pipeline.ru.md](ingest-pipeline.ru.md) · [🇬🇧](ingest-pipeline.md) — `/search` →
  сохранение метаданных → advisory lock → скачивание → извлечение → чанкинг → эмбеддинг →
  `indexed`; восстанавливаемый lifecycle и `/reindex`.
- [retrieval.ru.md](retrieval.ru.md) · [🇬🇧](retrieval.md) — hybrid search (dense `halfvec` +
  Postgres full-text + RRF), ready-only фильтрация, роутинг `/ask` (point vs synthesis),
  обоснованные ответы и map-reduce synthesis.
- [database.ru.md](database.ru.md) · [🇬🇧](database.md) — схема как она есть в `scripts/*.sql`
  (`papers`, `chunks`, `halfvec`, `text_search`, HNSW), backfill lifecycle и порядок файлов
  миграций.
- [enrichment.ru.md](enrichment.ru.md) · [🇬🇧](enrichment.md) — `summary_en` / `summary_ru` /
  `tags` от Gemini, отвязанные от `ingest_status`, пока не используются в retrieval.
- [bot-commands.ru.md](bot-commands.ru.md) · [🇬🇧](bot-commands.md) — операторская справка по
  `/start /search /ask /list /enrich /reindex` и inline-кнопкам ingest.
- [configuration.ru.md](configuration.ru.md) · [🇬🇧](configuration.md) — переменные окружения,
  Compose-сервисы `db`/`app`, зависимости и оговорка про ручную инициализацию схемы.

## Диаграммы

- [diagrams/README.ru.md](diagrams/README.ru.md) · [🇬🇧](diagrams/README.md) — Mermaid под-бандл:
  [ingest-flow](diagrams/ingest-flow.ru.md), [ask-flow](diagrams/ask-flow.ru.md) и
  [paper-lifecycle](diagrams/paper-lifecycle.ru.md). (Карта модулей — в
  [system-overview.ru.md](system-overview.ru.md).)

## Осталось

Набор as-built концептов + диаграмм завершён. Оставшаяся работа по бандлу:

- Per-file OKF frontmatter для `plan/01`–`plan/05` (пока помечен только
  [plan/README.md](plan/README.md)).
- Ревью человеком: перевести агентские черновики из `status: draft` в `verified` после проверки.

## Связанное (вне этого бандла)

- [../README.md](../README.md) — обзор проекта, установка, команды бота.
- [plan/README.md](plan/README.md) — проектное видение и роадмап (LangGraph, фазы hybrid
  retrieval, MCP). Помечено как vision; собрано не всё.
- [../specs/001-stabilize-rag-ingest/](../specs/001-stabilize-rag-ingest/spec.md) — активная
  Spec Kit фича (стабилизация ingest lifecycle).
