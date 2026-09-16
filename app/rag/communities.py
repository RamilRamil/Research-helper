import os
import uuid

import igraph as ig
import leidenalg
import psycopg


def _load_indexed_papers() -> list[dict]:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            """
            SELECT arxiv_id,
                   COALESCE(tags, '{}'),
                   COALESCE(categories, '{}'),
                   title,
                   COALESCE(summary_en, '')
            FROM papers
            WHERE ingest_status = 'indexed'
            ORDER BY arxiv_id
            """
        ).fetchall()
    out = []
    for arxiv_id, tags, categories, title, summary_en in rows:
        out.append(
            {
                "arxiv_id": arxiv_id,
                "tags": set(tags or []),
                "categories": set(categories or []),
                "title": title or "",
                "summary_en": summary_en or "",
            }
        )
    return out


def _edges(papers: list[dict]) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    n = len(papers)
    for i in range(n):
        a = papers[i]
        for j in range(i + 1, n):
            b = papers[j]
            if a["tags"] & b["tags"] or a["categories"] & b["categories"]:
                edges.append((i, j))
    return edges


def _summarize_group(members: list[dict]) -> str:
    ids = ", ".join(f"[{p['arxiv_id']}]" for p in members)
    notes: list[str] = []
    for p in members:
        raw = (p["summary_en"] or p["title"]).strip()
        if not raw:
            continue
        first = raw.split(".")[0].strip()
        notes.append(f"[{p['arxiv_id']}] {first}")
    body = "; ".join(notes[:8])
    if not body:
        return f"Community of {len(members)} papers: {ids}."
    return f"Community of {len(members)} papers: {ids}. {body}."


def _persist(groups: list[tuple[list[str], str]]) -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("UPDATE papers SET community_id = NULL")
        conn.execute("DELETE FROM communities")
        for arxiv_ids, summary in groups:
            cid = uuid.uuid4()
            conn.execute(
                "INSERT INTO communities (id, summary_en) VALUES (%s, %s)",
                (cid, summary),
            )
            conn.execute(
                """
                UPDATE papers
                SET community_id = %s,
                    updated_at = NOW()
                WHERE arxiv_id = ANY(%s)
                  AND ingest_status = 'indexed'
                """,
                (cid, arxiv_ids),
            )


def arxiv_ids_in_seed_communities(seed_ids: list[str]) -> list[str]:
    seeds = [s.split("v")[0] for s in seed_ids if s]
    if not seeds:
        return []
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT p2.arxiv_id
            FROM papers p1
            JOIN papers p2
              ON p2.ingest_status = 'indexed'
             AND p2.community_id IS NOT NULL
             AND p2.community_id = p1.community_id
            WHERE p1.arxiv_id = ANY(%s)
              AND p1.ingest_status = 'indexed'
              AND p1.community_id IS NOT NULL
            ORDER BY p2.arxiv_id
            """,
            (seeds,),
        ).fetchall()
    return [r[0] for r in rows]


def rebuild_communities() -> dict:
    papers = _load_indexed_papers()
    if not papers:
        _persist([])
        return {"n_papers": 0, "n_communities": 0, "sizes": []}

    g = ig.Graph(n=len(papers), edges=_edges(papers), directed=False)
    part = leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)

    groups: list[tuple[list[str], str]] = []
    sizes: list[int] = []
    for members in part:
        idxs = list(members)
        cluster = [papers[i] for i in idxs]
        arxiv_ids = [p["arxiv_id"] for p in cluster]
        summary = _summarize_group(cluster)
        groups.append((arxiv_ids, summary))
        sizes.append(len(arxiv_ids))

    _persist(groups)
    return {
        "n_papers": len(papers),
        "n_communities": len(groups),
        "sizes": sorted(sizes, reverse=True),
    }
