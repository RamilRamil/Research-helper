import os

import psycopg
from dotenv import load_dotenv

from app.tools.pdf_download import download_pdf, pdf_path
from app.tools.pdf_extract import extract_text
from app.db.papers import update_paper_pdf, mark_paper_indexed

load_dotenv()

MIN_TEXT_CHARS = 500


class IngestBusyError(RuntimeError):
    """Another ingest/reindex holds the lock for this arXiv ID."""


def _lock_key(arxiv_id: str) -> int:
    # stable signed 64-bit-ish key from id string
    clean = arxiv_id.split("v")[0]
    return abs(hash(clean)) % (2**31)


def ingest_paper(arxiv_id: str) -> str:
    clean = arxiv_id.split("v")[0]
    key = _lock_key(clean)

    with psycopg.connect(os.environ["DATABASE_URL"]) as lock_conn:
        row = lock_conn.execute(
            "SELECT pg_try_advisory_lock(%s)", (key,)
        ).fetchone()
        if not row or not row[0]:
            raise IngestBusyError(f"ingest already running for {clean}")

        try:
            path = download_pdf(clean)
            text, pages = extract_text(path)
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
        finally:
            lock_conn.execute("SELECT pg_advisory_unlock(%s)", (key,))