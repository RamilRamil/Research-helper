import hashlib
import os

import psycopg
from dotenv import load_dotenv

from app.tools.pdf_download import download_pdf, pdf_path
from app.tools.pdf_extract import extract_paper
from app.db.papers import update_paper_pdf, mark_paper_indexed

load_dotenv()

MIN_TEXT_CHARS = 500


class IngestBusyError(RuntimeError):
    """Another ingest/reindex holds the lock for this arXiv ID."""


def _lock_key(arxiv_id: str) -> int:
    # stable key from id string, process-independent (unlike builtin hash())
    clean = arxiv_id.split("v")[0]
    digest = hashlib.sha256(clean.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % (2**31)


def _ingest_body(clean: str) -> str:
    path = download_pdf(clean)
    text, pages = extract_paper(clean, path)
    if len(text) < MIN_TEXT_CHARS:
        raise ValueError(f"empty or scanned PDF: {clean}")
    update_paper_pdf(
        clean,
        pdf_local_path=str(path),
        page_count=pages,
        text_chars=len(text),
    )

    from app.db.chunks import save_chunks, embed_paper_chunks

    save_chunks(clean, text)
    embed_paper_chunks(clean)
    mark_paper_indexed(clean)
    return text


def _with_paper_lock(clean: str, fn):
    key = _lock_key(clean)
    with psycopg.connect(os.environ["DATABASE_URL"]) as lock_conn:
        row = lock_conn.execute(
            "SELECT pg_try_advisory_lock(%s)", (key,)
        ).fetchone()
        if not row or not row[0]:
            raise IngestBusyError(f"ingest already running for {clean}")
        try:
            return fn()
        finally:
            lock_conn.execute("SELECT pg_advisory_unlock(%s)", (key,))


def ingest_paper(arxiv_id: str) -> str:
    clean = arxiv_id.split("v")[0]
    return _with_paper_lock(clean, lambda: _ingest_body(clean))


def _rebuild_indexed_body(clean: str) -> str:
    from app.db.chunks import (
        save_chunks,
        embed_paper_chunks,
        drop_chunk_generation,
        promote_chunk_generation,
    )

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            """
            SELECT chunk_gen
            FROM papers
            WHERE arxiv_id = %s AND ingest_status = 'indexed'
            """,
            (clean,),
        ).fetchone()
    if not row:
        raise ValueError(f"paper not indexed: {clean}")
    nxt = int(row[0]) + 1
    try:
        path = download_pdf(clean)
        text, pages = extract_paper(clean, path)
        if len(text) < MIN_TEXT_CHARS:
            raise ValueError(f"empty or scanned PDF: {clean}")
        update_paper_pdf(
            clean,
            pdf_local_path=str(path),
            page_count=pages,
            text_chars=len(text),
            keep_indexed=True,
        )
        save_chunks(clean, text, generation=nxt)
        embed_paper_chunks(clean, generation=nxt)
        promote_chunk_generation(clean, nxt)
        return text
    except Exception:
        drop_chunk_generation(clean, nxt)
        raise


def reindex_paper(arxiv_id: str) -> str:
    """Lock first. Indexed: staged rebuild. Else: reset incomplete then ingest."""
    from app.db.papers import get_paper_status, prepare_reindex

    clean = arxiv_id.split("v")[0]

    def _run():
        status = get_paper_status(clean)
        if status is None:
            raise ValueError(f"paper not in database: {clean}")
        if status == "indexed":
            return _rebuild_indexed_body(clean)
        prepare_reindex(clean)
        return _ingest_body(clean)

    return _with_paper_lock(clean, _run)