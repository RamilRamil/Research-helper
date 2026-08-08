---
type: Reference
title: Индекс диаграмм
description: Mermaid flow- и state-диаграммы, отражающие что подключено сегодня; билингвально EN/RU.
tags: [index, diagrams]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
---

# Диаграммы

🇬🇧 [English version](README.md)

Flow- и state-диаграммы Research Helper, отражающие **что реально подключено сегодня**. Исходники
Mermaid, рендерятся в GitHub / VS Code / большинстве Markdown-вьюеров. **Карта модулей** — в
[../system-overview.ru.md](../system-overview.ru.md); этот под-бандл содержит flow/state-диаграммы.

- [ingest-flow.ru.md](ingest-flow.ru.md) · [🇬🇧](ingest-flow.md) — одна статья от кнопки `Add` до
  `indexed`: advisory lock, скачивание, извлечение, чанкинг, эмбеддинг, авто-enrich. В паре с
  [../ingest-pipeline.ru.md](../ingest-pipeline.ru.md).
- [ask-flow.ru.md](ask-flow.ru.md) · [🇬🇧](ask-flow.md) — `/ask`, роутинг point vs synthesis, плюс
  откат к сниппетам. В паре с [../retrieval.ru.md](../retrieval.ru.md).
- [paper-lifecycle.ru.md](paper-lifecycle.ru.md) · [🇬🇧](paper-lifecycle.md) — машина состояний
  `ingest_status` и legacy backfill.

Обновляй их при изменении проводки — диаграмма, которая врёт про то, что связано, хуже, чем её
отсутствие.
