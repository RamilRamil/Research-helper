from app.db.search import hybrid_search, search_chunks_in_papers
from app.rag.communities import arxiv_ids_in_seed_communities
from app.rag.crag import grade_support, rewrite_query
from app.rag.rerank import KEEP_SYNTHESIS, rerank_hits


def _seed_ids(hits: list[dict]) -> list[str]:
    ids: list[str] = []
    for h in hits:
        aid = h.get("arxiv_id")
        if aid and aid not in ids:
            ids.append(aid)
    return ids


def _expand(seed_ids: list[str]) -> list[str]:
    related = arxiv_ids_in_seed_communities(seed_ids)
    if related:
        return related
    return list(seed_ids)


def _rank_pool(question: str, pool: list[dict]) -> list[dict]:
    if not pool:
        return []
    return rerank_hits(question, pool, keep=KEEP_SYNTHESIS)


def retrieve_graph(question: str) -> list[dict]:
    q = question.strip()
    seed = hybrid_search(q, limit=10, fetch_k=20)
    seed_ids = _seed_ids(seed)
    union = _expand(seed_ids)
    pool = search_chunks_in_papers(q, union, limit=20) if union else seed
    ranked = _rank_pool(q, pool)
    if ranked and grade_support(q, ranked, kind="theme"):
        return ranked
    rewritten = rewrite_query(q)
    seed2 = hybrid_search(rewritten, limit=10, fetch_k=20)
    ids2 = _seed_ids(seed2)
    union2 = _expand(ids2)
    pool2 = search_chunks_in_papers(rewritten, union2, limit=20) if union2 else seed2
    ranked2 = _rank_pool(q, pool2)
    if ranked2 and grade_support(q, ranked2, kind="theme"):
        return ranked2
    return []
