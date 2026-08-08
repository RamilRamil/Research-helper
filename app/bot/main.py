import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED = int(os.environ["ALLOWED_USER_ID"])

bot = Bot(TOKEN)
dp = Dispatcher()

# last /search results per user: clean arxiv_ids (no version suffix)
_last_search: dict[int, list[str]] = {}


def is_allowed(user_id: int) -> bool:
    return user_id == ALLOWED


def _clean_id(arxiv_id: str) -> str:
    return arxiv_id.split("v")[0]


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return
    await message.answer("Hello! I'm your AI assistant. How can I help you today?")


@dp.message(Command("search"))
async def cmd_search(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /search <topic>")
        return

    topic = parts[1].strip()
    await message.answer(f"Searching arXiv: {topic} ...")

    from app.tools.arxiv_search import build_query, search_papers
    from app.db.papers import save_paper, get_paper_status

    papers = search_papers(topic, days=30, max_results=10)
    if not papers:
        await message.answer("No papers found")
        return

    search_query = build_query(topic)
    new_count = 0
    ids: list[str] = []

    for paper in papers:
        if save_paper(paper, topic, search_query):
            new_count += 1
        ids.append(_clean_id(paper["arxiv_id"]))

    _last_search[message.from_user.id] = ids

    lines = []
    for i, p in enumerate(papers, 1):
        clean = _clean_id(p["arxiv_id"])
        status = get_paper_status(clean) or "pending"
        lines.append(
            f"{i}. [{clean}] ({status}) {p['title']}\n"
            f"{p['published']} | {p['url']}"
        )

    rows = []
    for clean in ids:
        status = get_paper_status(clean) or "pending"
        label = f"Add {clean}" if status != "indexed" else f"Indexed {clean}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"add:{clean}")]
        )
    rows.append(
        [InlineKeyboardButton(text="Add all (not indexed)", callback_data="addall")]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    footer = (
        f"\n\nSaved metadata: {new_count} new, "
        f"{len(papers) - new_count} already in DB\n"
        f"Pick papers to ingest (PDF + embed)."
    )
    await message.answer("\n\n".join(lines) + footer, reply_markup=keyboard)


async def _ingest_one(arxiv_id: str) -> str:
    """Run ingest; return status line for Telegram."""
    from app.db.papers import get_paper_status, mark_paper_failed
    from app.tools.ingest_paper import ingest_paper, IngestBusyError

    clean = _clean_id(arxiv_id)
    status = get_paper_status(clean)
    if status == "indexed":
        return f"[{clean}] skipped (already indexed)"

    try:
        await asyncio.to_thread(ingest_paper, clean)
    except IngestBusyError as e:
        return f"[{clean}] busy: {e}"
    except Exception as e:
        mark_paper_failed(clean, str(e))
        return f"[{clean}] failed: {e}"

    from app.tools.enrich_paper import enrich_and_save

    try:
        await asyncio.to_thread(enrich_and_save, clean)
        return f"[{clean}] indexed ok + enriched"
    except Exception as e:
        return f"[{clean}] indexed ok; enrich failed: {e}"


@dp.callback_query(F.data.startswith("add:"))
async def on_add_one(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_allowed(callback.from_user.id):
        await callback.answer("Not allowed", show_alert=True)
        return

    clean = callback.data.split(":", 1)[1]
    await callback.answer(f"Ingesting {clean}...")
    await callback.message.answer(f"Ingesting {clean} ...")
    result = await _ingest_one(clean)
    await callback.message.answer(result)


@dp.callback_query(F.data == "addall")
async def on_add_all(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_allowed(callback.from_user.id):
        await callback.answer("Not allowed", show_alert=True)
        return

    ids = _last_search.get(callback.from_user.id) or []
    if not ids:
        await callback.answer("No last search", show_alert=True)
        return

    await callback.answer("Ingesting selected...")
    await callback.message.answer(f"Ingesting {len(ids)} papers from last search...")

    lines = []
    for clean in ids:
        lines.append(await _ingest_one(clean))
    await callback.message.answer("\n".join(lines))


@dp.message(Command("ask"))
async def cmd_ask(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /ask <question>")
        return

    question = parts[1].strip()

    from app.rag.router import route_question
    from app.db.search import hybrid_search
    from app.rag.answer import generate_answer
    from app.rag.synthesis import synthesize_answer

    mode = route_question(question)
    await message.answer(f"Thinking ({mode}): {question} ...")

    hits: list = []
    answer: str | None = None

    try:
        if mode == "synthesis":
            answer, hits = await asyncio.to_thread(synthesize_answer, question)
        else:
            hits = await asyncio.to_thread(hybrid_search, question, 5)
            if not hits:
                await message.answer("No relevant chunks found")
                return
            answer = await asyncio.to_thread(generate_answer, question, hits)
    except Exception as e:
        if not hits:
            await message.answer(f"Error: {e}")
            return
        await message.answer(
            f"Answer generation failed: {e}\nShowing retrieved snippets instead."
        )
        lines = []
        for i, h in enumerate(hits, 1):
            section = h.get("section") or "?"
            lines.append(
                f"{i}. [{h.get('arxiv_id')}] ({section})\n"
                f"{h.get('title')}\n"
                f"{h.get('snippet')}..."
            )
        await message.answer("\n\n".join(lines)[:4000])
        return

    if not answer:
        await message.answer("No relevant chunks found")
        return

    await message.answer(answer[:4000])

    seen: set[str] = set()
    sources = []
    for h in hits:
        aid = h.get("arxiv_id")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        sources.append(
            f"- [{aid}] {h.get('title')}\n  https://arxiv.org/abs/{aid}"
        )
    if sources:
        await message.answer("Sources:\n" + "\n".join(sources))


@dp.message(Command("list"))
async def cmd_list(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /list <topic>")
        return

    topic = parts[1].strip()
    await message.answer(f"Listing papers for: {topic} ...")

    from app.db.search import hybrid_search

    try:
        hits = await asyncio.to_thread(hybrid_search, topic, 15)
    except Exception as e:
        await message.answer(f"Error listing: {e}")
        return

    if not hits:
        await message.answer("No papers found in indexed library")
        return

    seen: set[str] = set()
    lines = []
    for h in hits:
        aid = h["arxiv_id"]
        if aid in seen:
            continue
        seen.add(aid)
        lines.append(
            f"{len(lines) + 1}. [{aid}] {h['title']}\n"
            f"https://arxiv.org/abs/{aid}"
        )
        if len(lines) >= 10:
            break

    await message.answer("\n\n".join(lines))


@dp.message(Command("enrich"))
async def cmd_enrich(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /enrich <arxiv_id>")
        return

    clean = _clean_id(parts[1].strip())
    await message.answer(f"Enriching {clean} ...")

    from app.db.papers import get_paper_status
    from app.tools.enrich_paper import enrich_and_save

    status = get_paper_status(clean)
    if status is None:
        await message.answer(f"paper not in database: {clean}")
        return

    try:
        card = await asyncio.to_thread(enrich_and_save, clean)
    except Exception as e:
        await message.answer(
            f"[{clean}] enrich failed (ingest_status unchanged={status}): {e}"
        )
        return

    tags = ", ".join(card.get("tags") or [])
    await message.answer(
        f"[{clean}] enriched ok (status={status})\n"
        f"EN: {card['summary_en']}\n\n"
        f"RU: {card['summary_ru']}\n\n"
        f"Tags: {tags}"
    )


@dp.message(Command("reindex"))
async def cmd_reindex(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /reindex <arxiv_id>")
        return

    raw_id = parts[1].strip()
    clean = _clean_id(raw_id)

    from app.db.papers import prepare_reindex, mark_paper_failed
    from app.tools.ingest_paper import ingest_paper, IngestBusyError
    from app.tools.enrich_paper import enrich_and_save

    try:
        prev = prepare_reindex(clean)
    except ValueError as e:
        await message.answer(str(e))
        return

    await message.answer(f"Reindexing {clean} (was {prev}) ...")

    try:
        await asyncio.to_thread(ingest_paper, clean)
    except IngestBusyError as e:
        await message.answer(f"[{clean}] busy: {e}")
        return
    except Exception as e:
        mark_paper_failed(clean, str(e))
        await message.answer(f"[{clean}] failed: {e}")
        return

    try:
        await asyncio.to_thread(enrich_and_save, clean)
        await message.answer(f"[{clean}] indexed ok + enriched")
    except Exception as e:
        await message.answer(f"[{clean}] indexed ok; enrich failed: {e}")




@dp.message(F.text)
async def any_text(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return
    await message.answer("Echo: " + message.text)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())