# RAG Upgrade Plan

Архитектурный backlog для RAG над научными статьями. Порядок реализации определяют
[`docs/plan/05-build-roadmap.md`](docs/plan/05-build-roadmap.md) и активная Spec Kit
feature. Этот документ описывает целевую RAG-стратегию, а не заменяет execution plan.

Апгрейд dense-only retrieval без генерации под специфику научных статей: жёсткая
структура документа + вопросы сравнения между статьями.

Базовый принцип: **PDF-хранение не убираем**. Своя база файлов (`data/papers/*.pdf`) остаётся
основным артефактом ingest'а. LaTeX-источник добавляется как *более чистый способ извлечь текст*,
с PDF как fallback, если e-print недоступен или не парсится.

Каждая фаза — отдельный шаг, не начинать следующую до подтверждения текущей. Пункты с новыми
библиотеками помечены отдельно — по вашим правилам это требует согласования до установки.

---

## Текущее состояние (baseline)

| Компонент | Файл | Как сейчас |
|---|---|---|
| Извлечение текста | `app/tools/pdf_extract.py`, `pdf_download.py` | Только PDF через PyMuPDF |
| Chunking | `app/rag/chunker.py` | Section-aware split + window 1000/200 внутри длинной секции |
| Эмбеддинги | `app/rag/embedder.py` | `gemini-embedding-001`, dense only |
| Поиск | `app/db/search.py` | Только dense cosine; без lifecycle filter, hybrid и HNSW |
| Хранилище | `scripts/add_chunks.sql`, `scripts/init_db.sql` | `papers`, `chunks` с `section`; без full-text индекса |
| Ответ бота | `app/bot/main.py` (`/ask`) | Отдаёт сырые сниппеты чанков, **без LLM-генерации и без цитирования** |

Основные разрывы: ingest lifecycle ещё не стабилизирован; нет hybrid-поиска,
генерации ответа с цитатами и разделения "точечный вопрос / вопрос-сравнение".

---

## Текущая фаза: Stabilize RAG Ingest

**Execution plan:** [`specs/001-stabilize-rag-ingest/`](specs/001-stabilize-rag-ingest/)
и Roadmap Phase 3.5.

До развития retrieval нужно закрыть:

1. Legacy backfill: классифицировать старые rows до ready-only retrieval.
2. Lifecycle: `pending -> text_ok -> indexed | failed`.
3. Normal `/search`: ingest только новых papers; `indexed` skip.
4. `/reindex <arxiv_id>`: только `pending`, `text_ok`, `failed`; `indexed` не менять.
5. PostgreSQL advisory lock на один arXiv ID.
6. Ready-only retrieval (`ingest_status = 'indexed'`).
7. HNSW после согласования vector type/operator с search query.

PDF остаётся локальным артефактом даже при failure.

---

## Фаза 1. Структурный chunking (реализовано, требуется проверка)

**Цель:** чанки привязаны к секции статьи, а не к произвольному окну символов.

Уже сделано:

1. `split_sections(text) -> list[dict]` по известным заголовкам.
2. Sliding window 1000/200 внутри длинной секции.
3. `chunks.section`, запись при ingest и возврат из search.

**Verify:** оценить section labels на пяти PDF: coverage, false positives, missed headings.

**Риск:** заголовки в PDF-тексте PyMuPDF часто "плывут" (двухколоночная вёрстка, отсутствие
переносов строк). Если после теста на 3-5 статьях detection секций совсем шумный — это аргумент
переходить к Фазе 2 раньше, чем откладывать её.

---

## Фаза 2. LaTeX-источник как приоритетный, PDF — fallback (conditional)

**Цель:** чище текст и точная разметка секций там, где есть e-print.

**Gate:** начинать только если оценка Фазы 1 показывает, что PyMuPDF section labels
недостаточно надёжны. PDF-download и локальное PDF-хранение не заменяются.

Таски:
1. Новый модуль `app/tools/latex_fetch.py`: скачать `.tar.gz` через `https://arxiv.org/e-print/{arxiv_id}`
   (либо `arxiv` lib, метод `download_source`), сохранить в `data/papers_src/{arxiv_id}/source.tar.gz`
   рядом с уже существующим `data/papers/{arxiv_id}.pdf` — PDF никуда не девается.
2. Распаковать архив, найти главный `.tex`-файл (эвристика: файл с `\documentclass`).
3. Парсинг `\section`/`\subsection`/`\abstract` в структуру `{section, text}` без сборки полного LaTeX
   AST — достаточно regex/построчного парсера под конкретные макросы, без рендеринга формул.
4. `app/tools/ingest_paper.py`: сначала пробовать `latex_fetch` → если exception/пустой результат →
   текущий путь `download_pdf` + `extract_text` (без изменений в PDF-логике).
5. `papers` таблица: добавить `source_type TEXT` (`latex` | `pdf`) и `latex_local_path TEXT` — для
   диагностики, из какого источника получен текст конкретной статьи.

**Новая зависимость (требует согласования):** парсер LaTeX — либо `TexSoup`, либо `pylatexenc`, либо
свой regex-парсер без новой либы (предпочтительно на старте, чтобы не тащить лишнее).

**Verify:** на 5 тестовых arxiv_id — сравнить `source_type` и количество секций vs PDF-путь для тех же
статей.

---

## Фаза 3. Hybrid-поиск: dense + full-text (Roadmap Phase 5)

**Цель:** точные термины/названия моделей не теряются в dense-similarity.

Таски:
1. Миграция `chunks`: добавить `text_search tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED`
   + `CREATE INDEX ... USING GIN (text_search)`. Это встроенный Postgres full-text — не BM25 в чистом виде,
   но closest без новых зависимостей (Elasticsearch/typesense/BM25-либа отдельно не поднимаем).
2. `app/db/search.py`: новая функция `full_text_search(query, limit)` через `to_tsquery`/`plainto_tsquery`.
3. Функция `hybrid_search(query, limit)`: dense top-N + full-text top-N → Reciprocal Rank Fusion (RRF)
   в Python, без новых либ.
4. Метаданные-фильтры: параметры `date_from`, `date_to`, `author` в `search_chunks`/`hybrid_search`,
   транслируются в `WHERE p.published_at >= ...` / `p.authors::text ILIKE ...`.

**Verify:** запрос с точным термином/названием модели (который дает плохой dense-хит) находит нужный
чанк через full-text ветку RRF.

---

## Фаза 4. Генерация ответа с цитированием в `/ask` (Roadmap Phase 6)

**Цель:** закрыть главную дыру — сейчас `/ask` отдаёт сниппеты, а не ответ.

Таски:
1. Новый модуль `app/rag/answer.py`: `generate_answer(question, hits) -> str`.
2. Промпт: контекст = список чанков с `{arxiv_id, title, section, text}`; жёсткое требование —
   каждое утверждение сопровождать `[arxiv_id]`; если в контексте нет ответа — модель должна сказать
   явно, а не придумывать.
3. `app/bot/main.py` (`cmd_ask`): после `search_chunks`/`hybrid_search` вызывать `generate_answer`,
   отправлять пользователю готовый ответ + список источников (`arxiv_id`, `title`, `url`) отдельным
   блоком под ответом.
4. Модель для генерации: Gemini (уже есть клиент в `app/rag/embedder.py`, переиспользовать `genai.Client`).

**Verify:** ответ на точечный вопрос по одной известной статье содержит корректный `[arxiv_id]` и не
смешивает факты с других статей в базе.

---

## Фаза 5. Routing: точечный вопрос vs вопрос-сравнение (Roadmap Phase 7)

**Цель:** синтетические вопросы ("чем отличаются подходы A и B") не должны идти через голый top-k
similarity — это ломается на 10+ статьях.

Таски:
1. `app/rag/router.py`: классификатор типа вопроса — либо простая heuristic (ключевые слова
   "сравни", "чем отличается", "какие подходы", "все статьи"), либо один короткий LLM-вызов
   с JSON-выводом `{"type": "point" | "synthesis"}`.
2. Ветка `point`: текущий pipeline Фазы 3+4 (hybrid search → generate_answer).
3. Ветка `synthesis`:
   - query decomposition: разбить вопрос на 2-4 подвопроса тем же LLM-вызовом;
   - retrieval по каждому подвопросу отдельно, дедуп чанков по `paper_id`;
   - map: короткое резюме релевантных чанков на каждую статью отдельно;
   - reduce: финальный ответ из резюме, с цитированием `[arxiv_id]` на уровне статьи, не чанка.
4. `cmd_ask` в `app/bot/main.py`: роутинг перед вызовом retrieval-пайплайна.

**Verify:** вопрос "чем отличаются методы X и Y" даёт ответ, покрывающий обе статьи, а не только
top-5 чанков с наибольшим cosine similarity к вопросу целиком.

---

## Фаза 6 (опционально, после оценки качества). Reranking и SPECTER2

Делать только если после Фаз 1-5 качество retrieval субъективно недостаточно — не аксиома, а проверка.

Таски:
1. Замерить текущее качество: 10-15 реальных вопросов → вручную оценить top-5 hits до/после Фаз 1-3.
2. Если dense плохо ранжирует релевантность (не путать с absence терминов — это чинится Фазой 3):
   добавить SPECTER2 как второй dense-вектор специально для scientific relevance ranking.
3. Если top-k после hybrid грязный (нерелевантные чанки в топе): добавить cross-encoder reranking
   top-20 → top-5 перед генерацией.

**Новая зависимость (требует согласования):** `sentence-transformers` (SPECTER2 + cross-encoder модели) —
локальный inference, увеличивает объём Docker-образа и требует CPU/RAM на обработку.

**Verify:** A/B на том же наборе из 10-15 вопросов, сравнение top-5 до/после.

---

## Изменения схемы БД по фазам (сводка)

```sql
-- Stabilize RAG Ingest
-- lifecycle backfill, HNSW index and query type alignment

-- Фаза 2 (conditional LaTeX)
ALTER TABLE papers ADD COLUMN source_type TEXT;         -- 'latex' | 'pdf'
ALTER TABLE papers ADD COLUMN latex_local_path TEXT;

-- Фаза 3
ALTER TABLE chunks ADD COLUMN text_search tsvector
    GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;
CREATE INDEX idx_chunks_text_search ON chunks USING GIN (text_search);
```

Каждая миграция — отдельный `.sql`-файл в `scripts/`, применяется только после согласования, по
аналогии с текущими `init_db.sql` / `add_chunks.sql`.

---

## Что сознательно НЕ делаем сейчас

- GROBID (отдельный сервис) — LaTeX + fallback PDF/PyMuPDF закрывает тот же кейс без нового
  контейнера в `docker-compose.yml`.
- Внешние поисковые движки (Elasticsearch/Qdrant/Chroma) — Postgres full-text + pgvector достаточно
  для объёма личной библиотеки статей.
- Fine-tuning эмбеддингов — нет eval-датасета, рано.
- Multi-agent оркестрация — не нужна. LangGraph, если понадобится, появляется только
  после Phases 4-7 как Roadmap Phase 8.

---

## Порядок выполнения

1. Roadmap Phase 3.5 / `specs/001-stabilize-rag-ingest/`.
2. Фаза 1: проверить реализованный structural chunking на пяти PDF.
3. Roadmap Phase 4: enrichment (summaries/tags), независимо от `indexed`.
4. Фаза 3 / Roadmap Phase 5: hybrid retrieval + filters + RRF.
5. Фаза 4 / Roadmap Phase 6: grounded answer с citations.
6. Фаза 5 / Roadmap Phase 7: routing и map-reduce synthesis.
7. Фаза 2 только при плохом результате section evaluation.
8. Фаза 6 только при измеримо недостаточном retrieval quality.

LangGraph — отдельная Roadmap Phase 8 поверх стабильных функций, не prerequisite для
этого пути.
