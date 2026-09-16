---
type: Reference
title: Команды бота — операторская справка
description: Командная поверхность Telegram — /start /search /ask /list /enrich /reindex /communities, inline-кнопки ingest и гейт ролей admin/reader.
tags: [telegram, commands, operator, reference]
lang: ru
status: draft
generated:
  by: research-helper/claude-opus-4.8
  at: 2026-08-08T16:00:14+04:00
sources:
  - resource: app/bot/main.py
    title: обработчики команд + callback'ов
---

# Команды бота — операторская справка

🇬🇧 [English version](bot-commands.md)

Каждый handler проверяет `app/bot/auth.py` против `ALLOWED_USERS` (или legacy `ALLOWED_USER_ID`).
Неизвестный id получает "You are not allowed to use this bot". Allowlisted без нужной роли —
"You are not allowed to use this command".

| Команда | Роли | Что делает |
|---|---|---|
| `/start` | admin, reader | Проверка доступа + приветствие. |
| `/search <topic>` | admin | Поиск на arXiv (последние 365 дней, до 10), сохраняет новые строки как `pending`, отвечает списком и per-paper кнопками ingest. |
| `/ask <question>` | admin, reader | Роутинг (point / synthesis / graph) с цитируемым блоком **Sources**. См. [retrieval.ru.md](retrieval.ru.md). |
| `/list <topic>` | admin, reader | `hybrid_search` по проиндексированной библиотеке, дедуп до топ-10 статей (без генерации). |
| `/enrich <arxiv_id>` | admin | (Пере)генерировать карточку RU/EN резюме + теги. Требует, чтобы статья была в БД. См. [enrichment.ru.md](enrichment.ru.md). |
| `/reindex <arxiv_id>` | admin | Incomplete ingest или staged-rebuild уже `indexed` (старые чанки ищутся, пока не свап). `/reindex indexed` — все indexed по очереди. |
| `/communities` | admin | Пересобрать Leiden-сообщества indexed-статей (общий tag или категория). Graph `/ask` расширяет seed до того же community. |
| любой другой текст | admin, reader | Эхо обратно. |
| ingest callbacks (`add:` / `addall`) | admin | Inline-кнопки из `/search`. |

## Inline-кнопки ingest

`/search` рендерит inline-клавиатуру:

- **`Add {id}`** (callback `add:{id}`) — проиндексировать одну статью через `_ingest_one`
  (пропускает, если уже `indexed`), затем авто-enrich. `Indexed {id}` показывается вместо неё, если
  статья уже проиндексирована.
- **`Add all (not indexed)`** (callback `addall`) — проиндексировать все статьи из последнего
  результата `/search` вызывающего, последовательно.

Полная последовательность ingest за кнопкой — в
[diagrams/ingest-flow.ru.md](diagrams/ingest-flow.ru.md).

## Заметки

- `/search` **только сохраняет метаданные** (`pending`); PDF скачиваются и эмбеддятся при нажатии
  кнопки, не во время поиска.
- Длинные ответы обрезаются под лимиты Telegram (ответы и откаты к сниппетам ограничены ~4000
  символов).
- Последний набор id из `/search` хранится **в памяти процесса** на пользователя (`_last_search`) —
  он не переживает рестарт бота, поэтому `Add all` требует свежего поиска после рестарта.
