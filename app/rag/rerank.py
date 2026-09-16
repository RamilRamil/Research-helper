import json
import re

from google.genai import types

from app.db.search import chunks_for_paper, full_text_search, hybrid_search
from app.rag.llm import generate_content
POOL = 20
KEEP_POINT = 5
KEEP_SYNTHESIS = 12
SNIPPET = 400
_ARXIV_ID = re.compile(r"^(\d{4}\.\d{4,5})(?:v\d+)?$")


def parse_arxiv_id(question: str) -> str | None:
    m = _ARXIV_ID.match((question or "").strip())
    return m.group(1) if m else None

_PROMPT = """Rank the passages for the question. Best first.

Return ONLY JSON:
{{"chunk_ids": ["id", "..."]}}

Use only ids from the list. Omit irrelevant ids.

Question:
{question}

Passages:
{passages}
"""


def _parse_ids(text: str) -> list[str]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    ids = data.get("chunk_ids")
    if not isinstance(ids, list):
        raise ValueError("rerank JSON missing chunk_ids list")
    out: list[str] = []
    for item in ids:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def rerank_hits(question: str, hits: list[dict], keep: int = KEEP_POINT) -> list[dict]:
    if not hits:
        raise ValueError("rerank_hits requires a non-empty pool")
    by_id: dict[str, dict] = {}
    lines = []
    for h in hits:
        cid = str(h.get("chunk_id") or "").strip()
        if not cid:
            raise ValueError("rerank pool item missing chunk_id")
        by_id[cid] = h
        text = (h.get("text") or h.get("snippet") or "").strip().replace("\x00", "")
        lines.append(f"- {cid}: {text[:SNIPPET]}")
    body = _PROMPT.format(question=question.strip(), passages="\n".join(lines))
    result = generate_content(
        body,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    text = (result.text or "").strip()
    if not text:
        raise ValueError("empty rerank response")
    ordered = _parse_ids(text)
    seen: set[str] = set()
    ranked: list[dict] = []
    for cid in ordered:
        if cid in seen or cid not in by_id:
            continue
        seen.add(cid)
        ranked.append(by_id[cid])
        if len(ranked) >= keep:
            break
    return ranked


def retrieve_for_ask(question: str, search: str = "hybrid") -> list[dict]:
    aid = parse_arxiv_id(question)
    if aid:
        pool = chunks_for_paper(aid, limit=POOL)
        return pool[:KEEP_POINT]
    if search == "fts":
        pool = full_text_search(question, limit=POOL)
    else:
        pool = hybrid_search(question, limit=POOL, fetch_k=POOL)
    if not pool:
        return []
    return rerank_hits(question, pool, keep=KEEP_POINT)
