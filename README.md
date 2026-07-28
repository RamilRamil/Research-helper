# Research Helper

Telegram bot for searching arXiv, indexing papers in PostgreSQL with pgvector, and answering questions over indexed paper fragments.

## Features

- Search recent arXiv papers by topic.
- Download and index selected PDFs.
- Generate embeddings and retrieve relevant paper fragments.
- Answer questions with Gemini and list source papers.
- Generate Russian and English paper summaries with tags.
- Limit bot access to one Telegram user.

## Stack

- Python 3.12
- aiogram
- PostgreSQL 16 with pgvector
- Google Gemini
- Docker Compose

## Setup

1. Create local environment file:

```bash
cp .env.example .env
```

2. Set values in `.env`:

```env
TELEGRAM_TOKEN=
ALLOWED_USER_ID=
GEMINI_API_KEY=
```

`DATABASE_URL` has a local default for direct execution. Docker Compose overrides it with its internal database address.

3. Start services:

```bash
docker compose up --build
```

The bot starts after PostgreSQL is healthy. Downloaded PDFs are stored locally in `data/papers/`.

## Bot commands

| Command | Description |
| --- | --- |
| `/start` | Check bot access |
| `/search <topic>` | Search arXiv and show papers for indexing |
| `/ask <question>` | Answer from indexed paper fragments |
| `/list <topic>` | List indexed papers relevant to topic |
| `/enrich <arxiv_id>` | Generate paper summaries and tags |
| `/reindex <arxiv_id>` | Re-download and index paper |

## Local development

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start database:

```bash
docker compose up -d db
```

Run bot:

```bash
python -m app.bot.main
```

## Security

- Never commit `.env`, API keys, Telegram token, or user identifiers.
- Keep downloaded PDFs and source archives out of git.
- Rotate exposed credentials before publishing repository.
