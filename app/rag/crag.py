import json
import re

from google.genai import types

from app.rag.llm import generate_content
from app.rag.rerank import retrieve_for_ask

_GRADE_PROMPT = """Does the context support answering the question using only
these passages? For a comparison question, sufficient is true if the passages
define or contrast the named concepts, even in a single paper.
Return ONLY JSON:
{{"sufficient": true}}
or
{{"sufficient": false}}

Question:
{question}

Context:
{context}
"""

_GRADE_THEME_PROMPT = """Do these passages mention the topic of the question
enough to list themes or related ideas? Do not require covering the whole
library. One or two on-topic papers is enough.
Return ONLY JSON:
{{"sufficient": true}}
or
{{"sufficient": false}}

Question:
{question}

Context:
{context}
"""

_REWRITE_PROMPT = """Rewrite the question as one English search query for a
scientific paper chunk index. Return ONLY JSON:
{{"query": "..."}}

Question:
{question}
"""

_GROUND_PROMPT = """Is every factual claim in the answer supported by the
context? Return ONLY JSON:
{{"grounded": true}}
or
{{"grounded": false}}

Question:
{question}

Answer:
{answer}

Context:
{context}
"""

_GROUND_THEME_PROMPT = """Are paper-specific claims in the answer supported by
the context? Listing themes from the given passages is grounded. Saying the
retrieve set is small or one paper is grounded. Invented papers or results
that are not in the context are not grounded.
Return ONLY JSON:
{{"grounded": true}}
or
{{"grounded": false}}

Question:
{question}

Answer:
{answer}

Context:
{context}
"""


def _parse_obj(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def _ctx(hits: list[dict], limit: int = 12) -> str:
    parts = []
    for h in hits[:limit]:
        aid = h.get("arxiv_id") or "?"
        text = (h.get("text") or h.get("snippet") or "").strip()[:500]
        parts.append(f"[{aid}] {text}")
    return "\n\n".join(parts)


def grade_support(question: str, hits: list[dict], *, kind: str = "default") -> bool:
    from app.rag.rerank import parse_arxiv_id

    aid = parse_arxiv_id(question)
    if aid and hits and any(h.get("arxiv_id") == aid for h in hits):
        return True
    prompt = _GRADE_THEME_PROMPT if kind == "theme" else _GRADE_PROMPT
    body = prompt.format(
        question=question.strip(),
        context=_ctx(hits),
    )
    result = generate_content(
        body,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    data = _parse_obj(result.text or "")
    return bool(data.get("sufficient"))


def rewrite_query(question: str) -> str:
    body = _REWRITE_PROMPT.format(question=question.strip())
    result = generate_content(
        body,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    data = _parse_obj(result.text or "")
    q = str(data.get("query") or "").strip()
    if not q:
        raise ValueError("empty rewrite query")
    return q


def retrieve_with_correction(question: str, search: str = "hybrid") -> list[dict]:
    q = question.strip()
    hits = retrieve_for_ask(q, search=search)
    if not hits:
        return []
    if grade_support(q, hits):
        return hits
    rewritten = rewrite_query(q)
    hits2 = retrieve_for_ask(rewritten, search=search)
    if not hits2:
        return []
    if grade_support(q, hits2):
        return hits2
    return []


def is_grounded(
    question: str, answer: str, hits: list[dict], *, kind: str = "default"
) -> bool:
    prompt = _GROUND_THEME_PROMPT if kind == "theme" else _GROUND_PROMPT
    body = prompt.format(
        question=question.strip(),
        answer=(answer or "").strip()[:4000],
        context=_ctx(hits),
    )
    result = generate_content(
        body,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    data = _parse_obj(result.text or "")
    return bool(data.get("grounded"))
