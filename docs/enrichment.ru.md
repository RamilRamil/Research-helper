---
type: Reference
title: Enrichment — карточки статей, отвязанные от ingest
description: summary_en / summary_ru / tags генерируются Gemini и сохраняются, не трогая ingest_status.
tags: [enrichment, summaries, tags, gemini]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/tools/enrich_paper.py
    title: enrich_and_save
  - resource: app/rag/enrich.py
    title: enrich_paper_card
  - resource: app/db/papers.py
    title: get_enrichment_input / save_paper_enrichment
---

# Enrichment — карточки статей

🇬🇧 [English version](enrichment.md)

Enrichment создаёт **карточку статьи** — `summary_en`, `summary_ru` и `tags` — для показа в
Telegram. Он намеренно **отвязан от индексации**: читает существующие строки и пишет только поля
карточки, никогда `ingest_status`.

## Входные данные

`get_enrichment_input` ([papers.py](../app/db/papers.py)) собирает вход модели из БД: `title`,
`abstract` и небольшой набор **выдержек** — первые два чанка плюс последний чанк (по `chunk_index`,
дедуплицированные). PDF повторно не читается.

## Генерация

`enrich_paper_card` ([enrich.py](../app/rag/enrich.py)) вызывает Gemini (`gemini-flash-latest`,
temperature 0.2, `response_mime_type=application/json`, 3 ретрая с backoff). Промпт просит
фактологичные `summary_en` (2–4 предложения), `summary_ru` и 3–8 коротких английских `tags`, без
выдуманных результатов. Ответ парсится как JSON и валидируется: оба резюме непусты, `tags` — список,
иначе ретрай / исключение.

## Сохранение

`save_paper_enrichment` пишет `summary_en`, `summary_ru`, `tags` и обновляет `updated_at`. Он **не
трогает `ingest_status`** — поэтому enrichment может успешно завершиться или упасть независимо от
того, проиндексирована статья или нет.

## Триггеры и изоляция сбоев

- **Автоматически** — успешный `ingest_paper` / `/reindex` сразу запускает `enrich_and_save`. Если
  enrichment падает, бот всё равно репортит статью как indexed (`"indexed ok; enrich failed: …"`), и
  статья остаётся доступной для поиска.
- **Вручную** — `/enrich <arxiv_id>` перегенерирует карточку для любой статьи, уже присутствующей в
  БД (`get_paper_status` не должен быть `None`); при сбое репортит и оставляет `ingest_status`
  неизменным.

## Пока не используется в retrieval

Карточка сохраняется (и у `tags` есть GIN-индекс), но **retrieval сегодня её не использует** —
`hybrid_search` ранжирует чанки, не резюме и не теги, а `/ask` / `/list` никогда не фильтруют по
`tags`. Enrichment сейчас обслуживает только карточку для человека. Проводка тегов/резюме в
retrieval — возможный будущий шаг, не подключённый.
