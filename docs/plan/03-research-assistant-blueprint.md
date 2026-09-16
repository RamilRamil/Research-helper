# Research Assistant Blueprint

Describes the **current** layout and the Knowledge Runtime *behavior* we want.
It is not a license to rewrite the tree into LangGraph/SQLAlchemy.

## Project structure (as-built)

```
AI assistant/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── app/
│   ├── bot/main.py              # aiogram, whitelist, commands
│   ├── tools/                   # arxiv_search, pdf_download, pdf_extract, ingest, enrich
│   ├── db/                      # papers, chunks, search (hybrid RRF)
│   └── rag/                     # chunker, embedder, router, answer, synthesis
├── scripts/                     # SQL and ops scripts
├── specs/                       # Spec Kit features (execution)
├── docs/plan/                   # this vision
├── data/papers/                 # PDF volume
└── RAG_UPGRADE_PLAN.md
```

New modules appear only when an active `tasks.md` names them. No `app/agent/graph.py`
until spec `005` (or a later agent spec) exists.

---

## arXiv search

- Free API, Python `arxiv` library, delay between bulk requests.
- Dedupe by `arxiv_id`.
- User RU topic may need EN query terms (existing search path).

Normal `/search`: create `pending` for new ids; skip `indexed`; report incomplete;
never mutate a working index.

---

## PDF ingest per paper

1. Lifecycle lookup (see 001).
2. Download `https://arxiv.org/pdf/{arxiv_id}.pdf` -> `data/papers/{arxiv_id}.pdf`.
3. Extract PyMuPDF; validate text length; `text_ok` or `failed` (PDF kept).
4. Chunk: detected section, then window 1000/200. Spec `003` may replace this.
5. Embed all chunks; then `indexed`.
6. Enrichment (summaries/tags) independent of searchable state.
7. `/reindex <arxiv_id>` only `pending` | `text_ok` | `failed`.

### Caps

| Limit | Value | Reason |
|-------|-------|--------|
| Max pages | configurable; code uses a page cap | quality/cost |
| Max papers per search | Telegram UX + quota | avoid blast radius |
| Concurrent ingest same arxiv_id | advisory lock | no double embed |

---

## Retrieval modes (today)

**Hybrid** (`hybrid_search`): dense top-N + FTS top-N -> RRF -> limit.

**Point `/ask`:** hybrid -> `generate_answer` with `[arxiv_id]` citations.

**Synthesis `/ask`:** heuristic route -> retrieve/synthesize across papers
(`synthesis.py`). Spec `005` replaces heuristic with planner/tool choice.

**Later `/ask`:** hybrid fetch_k -> rerank top-3/5 -> CRAG -> generate -> Self-RAG.

---

## Telegram UX (as-built plus 001)

| Command | Action |
|---------|--------|
| `/search` | arXiv + ingest new only |
| `/ask` | retrieve + grounded answer |
| `/reindex <arxiv_id>` | resume incomplete only |
| enrichment / summary commands | paper cards; must not un-index |

Exact command list: [../bot-commands.md](../bot-commands.md).

---

## Bilingual

| Component | Approach |
|-----------|----------|
| Summaries | RU and EN when enrichment runs |
| Bot replies | match user language where already implemented |
| Embeddings | Gemini multilingual |
| FTS config | `english` tsvector — RU exact terms may miss; do not silently add a second parser |

---

## Security (personal bot)

- `ALLOWED_USER_ID` whitelist.
- No document ACL in the vector index (deferred).
- URL fetch if added later: https only, block private IPs (SSRF).
- `ingest_error` must not store secrets.

---

## Dependencies

Follow `requirements.txt`. Do not add FastAPI, SQLAlchemy, LangGraph, sentence-transformers,
Ragas, or graph libraries from this document. Each belongs to a spec + explicit install
approval.
