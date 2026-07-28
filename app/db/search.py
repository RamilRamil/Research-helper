import os

import psycopg 
from dotenv import load_dotenv

from app.rag.embedder import embed_text

load_dotenv()


def search_chunks(query: str, limit: int = 5) -> list[dict]:
    vec = embed_text(query.strip(), for_query=True)

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        rows = conn.execute(
            """
            SELECT c.id,
                   p.arxiv_id,
                   p.title,
                   c.text,
                   c.section,
                   c.embedding <=> %s::halfvec(3072) AS distance
            FROM chunks c
            JOIN papers p ON p.id = c.paper_id
            WHERE c.embedding IS NOT NULL
              AND p.ingest_status = 'indexed'
            ORDER BY distance
            LIMIT %s
            """,
            (vec, limit),
        ).fetchall()

    results = []
    for chunk_id, arxiv_id, title, text, section, distance in rows:
        results.append(
            {
                "chunk_id": str(chunk_id),
                "arxiv_id": arxiv_id,
                "title": title,
                "text": text,
                "section": section,
                "snippet": text[:200],
                "distance": float(distance),
                "source": "dense",
            }
        )
    return results


def full_text_search(query: str, limit: int = 5) -> list[dict]:
    q = query.strip()
    if not q:
        return []

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        rows = conn.execute(
            """
            SELECT c.id,
                   p.arxiv_id,
                   p.title,
                   c.text,
                   c.section,
                   ts_rank(c.text_search, plainto_tsquery('english', %s)) AS rank
            FROM chunks c
            JOIN papers p ON p.id = c.paper_id
            WHERE p.ingest_status = 'indexed'
              AND c.text_search @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
            """,
            (q, q, limit),
        ).fetchall()

    results = []
    for chunk_id, arxiv_id, title, text, section, rank in rows:
        results.append(
            {
                "chunk_id": str(chunk_id),
                "arxiv_id": arxiv_id,
                "title": title,
                "text": text,
                "section": section,
                "snippet": text[:200],
                "rank": float(rank),
                "source": "fts",
            }
        )
    return results


def _rrf_fuse(
    ranked_lists: list[list[dict]],
    *,
    limit: int,
    k: int = 60,
) -> list[dict]:
    scores: dict[str, float] = {}
    best: dict[str, dict] = {}

    for hits in ranked_lists:
        for rank, hit in enumerate(hits, start=1):
            cid = hit["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            prev = best.get(cid)
            if prev is None:
                best[cid] = dict(hit)
            else:
                sources = {prev.get("source"), hit.get("source")}
                merged = dict(prev)
                merged.update(hit)
                if len(sources) > 1:
                    merged["source"] = "hybrid"
                best[cid] = merged

    ordered = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
    out = []
    for cid in ordered[:limit]:
        item = best[cid]
        item["rrf_score"] = scores[cid]
        out.append(item)
    return out


def hybrid_search(query: str, limit: int = 5, fetch_k: int = 20) -> list[dict]:
    """
    Dense top-fetch_k + FTS top-fetch_k -> RRF -> top limit.
    Dense still needs Gemini embed for the query.
    """
    q = query.strip()
    if not q:
        return []

    dense_hits = search_chunks(q, limit=fetch_k)
    fts_hits = full_text_search(q, limit=fetch_k)
    return _rrf_fuse([dense_hits, fts_hits], limit=limit)