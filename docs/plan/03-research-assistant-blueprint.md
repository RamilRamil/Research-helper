# Research Assistant Blueprint

## Project structure (future target)

Current project deliberately uses small `psycopg` modules and SQL files under
`scripts/`. Do not refactor into SQLAlchemy/Alembic or LangGraph before current
ingest/retrieval phases are stable.

```
research-agent/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── app/
│   ├── main.py                 # FastAPI health + optional webhook
│   ├── bot/
│   │   ├── telegram_bot.py     # aiogram handlers
│   │   ├── commands.py         # /research, /list, /summary, /status
│   │   └── auth.py             # whitelist user_id
│   ├── agent/
│   │   ├── graph.py            # LangGraph definition
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── nodes/
│   │   │   ├── router.py       # intent classification Groq
│   │   │   ├── parse_query.py  # topic, dates, source preference
│   │   │   ├── translate_query.py  # RU -> EN for arXiv
│   │   │   ├── search_arxiv.py
│   │   │   ├── ingest.py       # dedupe + PDF + summarize + store
│   │   │   ├── retrieve.py     # search KB
│   │   │   ├── summarize_kb.py # synthesis report
│   │   │   └── respond.py
│   │   └── prompts/
│   │       ├── router.txt
│   │       ├── paper_summary.txt
│   │       └── topic_synthesis.txt
│   ├── tools/
│   │   ├── arxiv_search.py
│   │   ├── arxiv_fetch.py      # PDF download
│   │   ├── pdf_extract.py      # PyMuPDF
│   │   └── kb_search.py
│   ├── db/
│   │   ├── models.py           # SQLAlchemy
│   │   ├── repository.py
│   │   └── migrations/         # alembic
│   ├── rag/
│   │   ├── chunker.py
│   │   ├── embedder.py         # Gemini embeddings
│   │   └── indexer.py
│   ├── backup/
│   │   └── export.py           # JSONL to volume
│   └── config.py
├── data/
│   ├── papers/                 # PDF files Docker volume
│   └── backups/                # JSONL exports
└── notebooks/
    └── colab_reindex.ipynb     # batch re-embed optional
```

---

## AgentState (LangGraph)

```python
{
    "user_message": str,
    "intent": "find_papers | list_all | topic_summary | clarify",
    "topic": str,                    # e.g. "MEV web3"
    "date_from": date,
    "date_to": date,
    "language": str,                 # "ru" | "en"
    "arxiv_results": list[dict],
    "new_papers": list[dict],
    "kb_hits": list[dict],
    "response_text": str,
}
```

---

## arXiv search

### API

- Free, no API key
- Python library: `arxiv`
- Rate limit: ~3 seconds between bulk requests

### Example query construction

User message: `find papers from the last month on MEV in web3`

Parsed:
- `date_from` = today - 30 days
- `date_to` = today
- `topic` = MEV web3

arXiv query string:

```
(submittedDate:[20250603 TO 20250703]) AND (
  all:MEV OR all:"maximal extractable value" OR all:"miner extractable value"
) AND (
  all:web3 OR all:blockchain OR all:ethereum OR all:defi OR all:"smart contract"
)
```

Sort: `-submittedDate` (newest first)
Limit: 20-50 per request (configurable)

### Router output (JSON)

```json
{
  "intent": "find_papers",
  "topic": "MEV in web3",
  "date_range_days": 30,
  "language": "ru"
}
```

---

## PDF ingest per paper

1. **State lookup:** normal search creates a new `pending` row or skips an existing
   `indexed` row.
2. **Download:** `https://arxiv.org/pdf/{arxiv_id}.pdf` -> `data/papers/{arxiv_id}.pdf`
3. **Extract:** PyMuPDF page-by-page; validate `text_chars >= 500`
4. **Lifecycle:** successful extraction sets `text_ok`; any failure sets `failed`
   with safe diagnostic while retaining downloaded PDF.
5. **Chunk:** split by detected section, then window long sections.
6. **Embed:** each chunk; after all embeddings succeed set `ingest_status = indexed`.
7. **Summarize later:** paper enrichment is independent from searchable state:
   ```json
   {
     "summary_en": "...",
     "summary_ru": "...",
     "tags": ["MEV", "ethereum", "auction"]
   }
   ```
8. **Recovery:** `/reindex <arxiv_id>` may resume only `pending`, `text_ok`, or
   `failed`; it rejects `indexed` rows until staged indexing exists.
9. **Backup later:** append JSONL after a successful `indexed` ingest.

### Caps (MVP)

| Limit | Value | Reason |
|-------|-------|--------|
| Max pages to index | configurable; current code uses 100 | quality/cost trade-off |
| Max chars | 200000 | memory |
| Max papers per search | 30 | Telegram UX + API quota |
| Max summaries per day | 100 | quota protection |

---

## Retrieval modes

### A) List everything on topic (`list_all`)

Hybrid retrieval:
1. SQL filter: tags, ILIKE on title/abstract
2. Vector search: embed query, top-K chunks, group by paper_id
3. Merge and dedupe, sort by `published_at DESC`

Output: numbered list with arxiv_id, title, one-liner, pdf_url

### B) Topic summary (`topic_summary`)

1. Vector search top 30 chunks
2. Group by paper_id, top 3-5 chunks per paper
3. Add `summary_ru` / `summary_en` from papers table
4. Gemini synthesis with mandatory `[arxiv_id]` citations
5. Respond in user language

---

## Telegram UX

| Command / phrase | Action |
|------------------|--------|
| Free text "find..." | `find_papers` pipeline |
| `/list MEV` | list from KB |
| `/summary MEV` | synthesis from KB |
| `/paper 2406.01234` | single paper card |
| `/stats` | paper count, last ingest, API usage |
| `/backup` | force JSONL export |
| `/reindex 2406.01234` | resume only `pending`, `text_ok`, or `failed` paper |

### Progress messages (long ingest)

```
Searching arXiv... done (14 hits)
[1/9] 2406.01234 downloading...
[1/9] extracting, 42 chunks, embedding...
[2/9] ...
Done: 9 new, 5 skipped.
```

---

## Bilingual (RU + EN)

| Component | Approach |
|-----------|----------|
| Summaries at ingest | generate both RU and EN |
| Bot replies | match user message language |
| Embeddings | multilingual model (Gemini embedding) |
| arXiv search | translate RU topic to EN before query |

---

## Backup strategy

```
Primary write:  Supabase or local Postgres
PDF files:      data/papers/ Docker volume
Async backup:   append JSONL after each successful ingest
Daily:          manifest with arxiv_ids + chunk counts
Weekly:         copy data/papers/ and backups/ to external disk
```

Do NOT run two live DBs with bidirectional sync. Use primary + append-only backup.

---

## Security (personal bot)

```python
ALLOWED_USER_IDS = {your_telegram_id}
MAX_PAPERS_PER_SEARCH = 30
MAX_SUMMARIES_PER_DAY = 100
ARXIV_REQUEST_DELAY_SEC = 3
```

URL fetch (if added later): https only, block private IP ranges (SSRF).

---

## Example dialog

**User:** find papers from the last month on MEV in web3

**Bot:**
```
Searching arXiv (2025-06-03 - 2025-07-03)...
Found 14, new 9, already in DB 5.

1. 2406.01234 - MEV Mitigation on Rollups...
   RU: MEV na L2 i aukciony sequencers...
   https://arxiv.org/abs/2406.01234
2. ...
```

**User (later):** brief summary on everything I have on MEV

**Bot:**
```
## Summary: MEV / web3 (9 papers in library)

Trends: ...
Key works: [2406.01234], [2405.09876]
Open questions: ...
```

---

## Dependencies (reference)

```
aiogram>=3.4
fastapi
sqlalchemy>=2
alembic
asyncpg
pgvector
arxiv
pymupdf
httpx
langgraph
langchain-google-genai
groq
python-dotenv
tenacity
```
