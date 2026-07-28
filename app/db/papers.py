import os 

from dotenv import load_dotenv
import psycopg 

load_dotenv()


def save_paper(paper: dict, topic: str, search_query: str) -> bool:
    """Returns True if new row inserted, False if row already exists"""
    arxiv_id = paper["arxiv_id"].split("v")[0]

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        cur = conn.execute(
            """
            INSERT INTO papers (
                arxiv_id, title, abstract, authors, published_at,
                pdf_url, ingest_status, found_by_query, search_query
            )
            VALUES (
                %s, %s, %s, %s::jsonb, %s,
                %s, 'pending', %s, %s
            )
            ON CONFLICT (arxiv_id) DO NOTHING
            RETURNING id
            """,
            (
                arxiv_id,
                paper["title"],
                paper.get("abstract"),
                psycopg.types.json.Json(paper.get("authors") or []),
                paper["published"],
                paper.get("pdf_url"),
                topic,
                search_query,
            ),
        )
        return cur.fetchone() is not None


def update_paper_pdf(arxiv_id: str, pdf_local_path: str, page_count: int, text_chars: int) -> None:
    clean_id = arxiv_id.split("v")[0]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE papers
            SET pdf_local_path = %s,
                page_count = %s,
                text_chars = %s,
                ingest_status = 'text_ok',
                updated_at = NOW()
            WHERE arxiv_id = %s
            """,
            (pdf_local_path, page_count, text_chars, clean_id)
        )


def get_paper_status(arxiv_id: str) -> str | None:
    """Return ingest_status or None if paper not found"""
    clean_id = arxiv_id.split("v")[0]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            "SELECT ingest_status FROM papers WHERE arxiv_id = %s",
            (clean_id,),
        ).fetchone()
        if not row:
            return None
        return row[0]


def mark_paper_indexed(arxiv_id: str) -> None:
    clean_id = arxiv_id.split("v")[0]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE papers
            SET ingest_status = 'indexed',
                ingest_error = NULL,
                updated_at = NOW()
            WHERE arxiv_id = %s
            """,
            (clean_id,),
        )
def mark_paper_failed(arxiv_id: str, error: str) -> None:
    """Set failed state. Does not clear pdf_local_path."""
    clean_id = arxiv_id.split("v")[0]
    safe = (error or "unknown error").replace("\x00", "")[:500]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE papers
            SET ingest_status = 'failed',
                ingest_error = %s,
                updated_at = NOW()
            WHERE arxiv_id = %s
            """,
            (safe, clean_id),
        )


def prepare_reindex(arxiv_id: str) -> str:
    """
    Allow reindex only for pending/text_ok/failed.
    Returns current status before reset.
    Raises ValueError if missing or indexed.
    """
    clean_id = arxiv_id.split("v")[0]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            "SELECT ingest_status FROM papers WHERE arxiv_id = %s",
            (clean_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"paper not in database: {clean_id}")
        status = row[0]
        if status == "indexed":
            raise ValueError(f"paper already indexed: {clean_id}")
        if status not in ("pending", "text_ok", "failed"):
            raise ValueError(f"unsupported status {status}: {clean_id}")
        conn.execute(
            """
            UPDATE papers
            SET ingest_status = 'pending',
                ingest_error = NULL,
                updated_at = NOW()
            WHERE arxiv_id = %s
            """,
            (clean_id,),
        )
    return status


def get_enrichment_input(arxiv_id: str) -> dict:
    """
    Build enrich_paper_card inputs from DB.
    Raises ValueError if paper missing.
    """
    clean_id = arxiv_id.split("v")[0]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            """
            SELECT id, title, abstract
            FROM papers
            WHERE arxiv_id = %s
            """,
            (clean_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"paper not in database: {clean_id}")
        paper_id, title, abstract = row

        chunk_rows = conn.execute(
            """
            SELECT text
            FROM chunks
            WHERE paper_id = %s
            ORDER BY chunk_index
            """,
            (paper_id,),
        ).fetchall()

    texts = [r[0] for r in chunk_rows if r[0]]
    excerpts: list[str] = []
    if texts:
        excerpts.extend(texts[:2])
        if len(texts) > 2:
            last = texts[-1]
            if last not in excerpts:
                excerpts.append(last)

    return {
        "arxiv_id": clean_id,
        "title": title or "",
        "abstract": abstract,
        "excerpts": excerpts,
    }


def save_paper_enrichment(
    arxiv_id: str,
    *,
    summary_en: str,
    summary_ru: str,
    tags: list[str],
) -> None:
    """Write card fields only. Does not touch ingest_status."""
    clean_id = arxiv_id.split("v")[0]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE papers
            SET summary_en = %s,
                summary_ru = %s,
                tags = %s,
                updated_at = NOW()
            WHERE arxiv_id = %s
            """,
            (summary_en, summary_ru, tags, clean_id),
        )