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

    papers = search_papers(topic, days=365, max_results=10)
    if not papers:
        await message.answer("No papers found")
        return

    search_query = build_query(topic)
    new_count = 0
    skipped_indexed = 0
    incomplete_count = 0
    ids: list[str] = []

    for paper in papers:
        inserted = save_paper(paper, topic, search_query)
        clean = _clean_id(paper["arxiv_id"])
        ids.append(clean)
        if inserted:
            new_count += 1
            continue
        status = get_paper_status(clean)
        if status == "indexed":
            skipped_indexed += 1
        else:
            incomplete_count += 1

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
        f"{skipped_indexed} skipped indexed, "
        f"{incomplete_count} incomplete (use /reindex)\n"
        f"Pick pending papers to ingest (PDF + embed)."
    )
    await message.answer("\n\n".join(lines) + footer, reply_markup=keyboard)


async def _ingest_one(arxiv_id: str) -> str:
    """Run ingest; return status line for Telegram."""
    from app.db.papers import get_paper_status, mark_paper_failed
    from app.tools.ingest_paper import ingest_paper, IngestBusyError

    clean = _clean_id(arxiv_id)
    status = get_paper_status(clean)
    if status is None:
        return f"[{clean}] not in database"
    if status == "indexed":
        return f"[{clean}] skipped (already indexed)"
    if status in ("text_ok", "failed"):
        return f"[{clean}] incomplete ({status}); use /reindex {clean}"

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

    from app.rag.ask import run_ask
    from app.rag.trace import log_ask

    rec = await asyncio.to_thread(run_ask, question)
    hits = rec.get("hits") or []
    answer = rec.get("answer")

    try:
        await message.answer(f"Thinking ({rec.get('route') or '?'}): {question} ...")

        if rec["outcome"] == "error":
            rec["n_hits"] = len(hits)
            if not hits:
                await message.answer(f"Error: {rec.get('error') or 'unknown'}")
                return
            await message.answer(
                f"Answer generation failed: {rec.get('error')}\n"
                "Showing retrieved snippets instead."
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

        if rec["outcome"] == "refuse_support":
            await message.answer(
                rec.get("answer") or "Indexed library cannot support this question."
            )
            return

        if rec["outcome"] == "refuse_grounded":
            await message.answer("Answer failed groundedness check.")
            return

        if not answer:
            rec["outcome"] = "refuse_support"
            await message.answer("No relevant chunks found")
            return

        await message.answer(str(answer)[:4000])

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
    except Exception as e:
        rec["outcome"] = "error"
        rec["error"] = str(e)[:300]
        rec["n_hits"] = len(hits)
        await message.answer(f"Error: {e}")
        return
    finally:
        log_row = {
            "question": rec.get("question"),
            "route": rec.get("route"),
            "tool": rec.get("tool"),
            "outcome": rec.get("outcome"),
            "n_hits": rec.get("n_hits"),
            "arxiv_ids": rec.get("arxiv_ids"),
            "error": rec.get("error"),
        }
        log_ask(log_row)


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


@dp.message(Command("communities"))
async def cmd_communities(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    await message.answer("Rebuilding Leiden communities ...")
    from app.rag.communities import rebuild_communities

    try:
        stats = await asyncio.to_thread(rebuild_communities)
    except Exception as e:
        await message.answer(f"Community rebuild failed: {e}")
        return

    sizes = ", ".join(str(n) for n in stats["sizes"]) or "none"
    await message.answer(
        f"Communities rebuilt: {stats['n_communities']} groups, "
        f"{stats['n_papers']} indexed papers. Sizes: {sizes}"
    )


@dp.message(Command("reindex"))
async def cmd_reindex(message: Message) -> None:
    if not is_allowed(message.from_user.id):
        await message.answer("You are not allowed to use this bot")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("Usage: /reindex <arxiv_id> or /reindex indexed")
        return

    raw_id = parts[1].strip()
    if raw_id.lower() == "indexed":
        from app.db.papers import list_indexed_arxiv_ids, note_indexed_rebuild_error
        from app.tools.ingest_paper import reindex_paper, IngestBusyError
        from app.tools.enrich_paper import enrich_and_save

        ids = list_indexed_arxiv_ids()
        if not ids:
            await message.answer("No indexed papers")
            return
        await message.answer(f"Reindexing {len(ids)} indexed papers ...")
        for clean in ids:
            try:
                await asyncio.to_thread(reindex_paper, clean)
            except IngestBusyError as e:
                await message.answer(f"[{clean}] busy: {e}")
                continue
            except Exception as e:
                note_indexed_rebuild_error(clean, str(e))
                await message.answer(f"[{clean}] rebuild failed: {e}")
                continue
            try:
                await asyncio.to_thread(enrich_and_save, clean)
                await message.answer(f"[{clean}] rebuilt ok + enriched")
            except Exception as e:
                await message.answer(f"[{clean}] rebuilt ok; enrich failed: {e}")
        return

    clean = _clean_id(raw_id)

    from app.db.papers import get_paper_status, mark_paper_failed, note_indexed_rebuild_error
    from app.tools.ingest_paper import reindex_paper, IngestBusyError
    from app.tools.enrich_paper import enrich_and_save

    await message.answer(f"Reindexing {clean} ...")

    was_indexed = get_paper_status(clean) == "indexed"
    try:
        await asyncio.to_thread(reindex_paper, clean)
    except IngestBusyError as e:
        await message.answer(f"[{clean}] busy: {e}")
        return
    except ValueError as e:
        await message.answer(str(e))
        return
    except Exception as e:
        if was_indexed:
            note_indexed_rebuild_error(clean, str(e))
            await message.answer(f"[{clean}] rebuild failed; previous index kept: {e}")
        else:
            mark_paper_failed(clean, str(e))
            await message.answer(f"[{clean}] failed: {e}")
        return

    try:
        await asyncio.to_thread(enrich_and_save, clean)
        msg = "rebuilt ok + enriched" if was_indexed else "indexed ok + enriched"
        await message.answer(f"[{clean}] {msg}")
    except Exception as e:
        msg = "rebuilt ok" if was_indexed else "indexed ok"
        await message.answer(f"[{clean}] {msg}; enrich failed: {e}")




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