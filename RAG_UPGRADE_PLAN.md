# RAG Upgrade Plan

Целевая система: **Knowledge Runtime** над локальной библиотекой arXiv PDF.
Файл — **стратегия**. Исполнение только через активную Spec Kit feature
(`specs/NNN-*/` + `tasks.md`). Новые библиотеки — согласовать до install.

Constitution: [`.specify/memory/constitution.md`](.specify/memory/constitution.md).
Индекс specs: [`specs/README.md`](specs/README.md).
Диаграммы / схема: [`docs/plan/`](docs/plan/README.md).

## Принципы

- PDF в `data/papers/*.pdf` не убираем. TeX e-print — более чистый текст; PDF остаётся.
- Retrieval только `ingest_status = 'indexed'`. `/search` не мутирует `indexed`.
- Incomplete / stale index — явный `/reindex` (staged swap, `chunk_gen`).
- Groundedness: нет опоры в контексте — отказ, не догадка.
- Одна feature = один столп или узкий срез.
- Read-only local MCP server отдаёт indexed library; MCP clients и внешние
  источники — вне scope.
- Retrieval-native paper ACL — отложено (shared library; Telegram roles +
  MCP per-user credentials без фильтров по papers).
- Eval не vibes: регрессия измерима (traces сейчас, Ragas — `012`).

Не делаем: GROBID, Elasticsearch, Qdrant, fine-tune эмбеддингов, web-fallback CRAG,
entity-level GraphRAG, MCPD-чанкинг (вместо него `003` section-aware).

## As-built

| Компонент | Где | Сейчас |
|---|---|---|
| Extract | `pdf_extract.py` | TeX e-print если `.tex` ≥500 chars, иначе PyMuPDF |
| Chunking | `chunker.py` | Section-aware, cap 1000 / overlap 200; не MCPD |
| Embed | `embedder.py` | `gemini-embedding-001`, `halfvec(3072)` |
| Hybrid | `search.py` | dense cosine + FTS + RRF; live `chunk_gen` |
| Rerank | `rerank.py` | LLM listwise по `chunk_ids` (не отдельный cross-encoder) |
| CRAG | `crag.py` | grade / rewrite / groundedness; без web |
| Router | `router.py` | LLM `point` / `synthesis` / `graph` |
| Answer | `answer.py`, `synthesis.py` | DeepSeek V3.2 via OpenRouter; цитаты `[arxiv_id]` |
| Graph | `graph.py`, `communities.py` | tag/category граф, Leiden, hop по `community_id` |
| Traces | `trace.py` | JSONL на `/ask` |
| Ingest | papers + `001`/`009` | `pending → text_ok → indexed \| failed`; staged rebuild |
| MCP | `mcp_server.py` | read-only stdio + Streamable HTTP (`--http`, Bearer + rate limit) |

## Specs

Живой статус: [`specs/README.md`](specs/README.md). Active: `.specify/feature.json`
(сейчас `025-mcp-topic-ingest`, verified).

| Spec | Столп | Статус |
|---|---|---|
| `001` | ingest integrity | verified |
| `002` | two-stage + rerank | live |
| `003` | semantic chunking (section-aware) | код live; индекс частично старый |
| `004` | CRAG / Self-RAG | live |
| `005` | query routing | live |
| `006` | observability (traces) | live; Ragas не здесь |
| `007` | paper graph hop | live |
| `008` | cite + category hop | live; graph retrieve больше не tag-hop |
| `009` | staged reindex | drain done: 32 indexed on live chunk_gen |
| `010` | LaTeX-first extract | TeX extract live; T002 ok on 2607.18826 |
| `011` | Leiden communities | persist + `/communities`; graph `/ask` verified 2026-09-15 |
| `012` | Ragas eval | live; `data/papers/_ragas_eval.json` |
| `013` | graph ask faithfulness | verified: 0.91 / ~1.00; 5 sources |
| `014` | embed quota fail-closed | Gemini 3072 only; no second embedder |
| `015` | DeepSeek V3.2 chat | OpenRouter generate; Gemini embed |
| `016` | supply-chain pins | verified; exact `==` install set |
| `017` | MCP library server | verified: read-only stdio; list/get/search |
| `018` | MCP HTTP auth | verified: Streamable HTTP + token + rate limit |
| `019` | Telegram roles | verified: multi-user `admin`/`reader`; legacy `ALLOWED_USER_ID`; MCP unchanged |
| `020` | MCP per-user tokens | verified: DB credentials; no shared env token; dual rate limits |
| `024` | MCP paper chunks | verified: `get_paper_chunks` paging |
| `025` | MCP topic ingest jobs | verified: admin enqueue + poll; async search/index worker |
| — | OAuth / paper ACL | deferred |

Hybrid + RRF не отдельная фича: было as-built до `002`. `002` — rerank поверх hybrid.

## Очередь (не новые столпы)

Очередь долгов (Spec Kit, по одному):

1. ~~`013`~~ graph `/ask` faithfulness 0.91 (floor 0.60).
2. ~~`014`~~ embed quota fail-closed (one Gemini model).
3. ~~`015`~~ DeepSeek V3.2 chat (OpenRouter).
4. ~~`016`~~ exact pins from live freeze.
5. ~~`017`~~ local read-only MCP server.
6. ~~`018`~~ MCP Streamable HTTP + shared Bearer + rate limit (TLS via reverse proxy).
7. ~~`019`~~ Telegram multi-user roles (`admin`/`reader`).
8. ~~`020`~~ MCP per-user HTTP credentials (DB; no shared env token).
9. ~~`024`~~ MCP `get_paper_chunks` (paged full-paper text).
10. ~~`025`~~ MCP admin topic ingest jobs (async + poll).
11. Later: OAuth/OIDC; paper-level ACL.

## Столпы — что закрыто чем

1. **Chunking** — `003` (секции + окно). MCPD / агентный чанк — не в backlog.
2. **Hybrid** — as-built Postgres.
3. **Rerank** — `002` LLM rerank.
4. **GraphRAG** — paper graph `007`/`008` + Leiden `011`. Не entity graph.
5. **Agentic** — `005` router, не многошаговый planner с отдельными tools.
6. **CRAG / Self-RAG** — `004`. Web не делаем.
7. **ACL** — `019` Telegram roles + `020` MCP per-user HTTP credentials
   (shared library). OAuth / paper ACL later.
8. **Eval** — traces `006`; метрики Ragas — `012`.

## Схема БД

База: [`docs/plan/04-database-schema.md`](docs/plan/04-database-schema.md).
Накатанные добавки: `scripts/chunk_gen.sql`, `scripts/communities.sql`.
Новые колонки — только миграцией в `scripts/` активной feature.

## Порядок работы агента

```
active feature.json → только её tasks.md
  → стоп после крупного куска
  → следующая feature только по «делай»
```

Локальный MCP (`017`), HTTP (`018`/`020`), Telegram roles (`019`) и
`get_paper_chunks` (`024`) закрыты.
Локальный MCP (`017`/`020`/`024`), HTTP + topic ingest jobs (`025`) закрыты.
Next: OAuth / paper ACL — позже.
