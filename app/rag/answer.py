import re

from google.genai import types

from app.rag.llm import generate_content

_PROMPT = """You answer a research question using ONLY the context chunks below.

Rules:
- Every factual claim must cite sources as [arxiv_id] using ids from the context.
- Never cite with [1], [2], or other numeric indexes. Context lines are already keyed by arxiv_id.
- If several chunks support a claim, you may write [id1][id2].
- If the context is insufficient, say so clearly. Do not invent papers or results.
- Prefer concise answers (short paragraphs or bullets).
- You may answer in the same language as the question.

Question:
{question}

Context:
{context}
"""

_PROMPT_THEME = """You list themes from ONLY the context chunks below.

Rules:
- Every bullet must restate a claim that appears in the context. No extra papers,
  venues, or results.
- Cite [arxiv_id] from the context. Never cite with [1] or [2].
- Do not claim a full-library survey. Say how many arxiv_id values are in the
  context.
- If only one arxiv_id is present, list themes from that paper and say it is the
  only source in this retrieve.
- Prefer short bullets.

Question:
{question}

Context:
{context}
"""


def _format_context(hits: list[dict]) -> str:
    parts = []
    for h in hits:
        section = h.get("section") or "?"
        aid = h.get("arxiv_id") or "?"
        text = (h.get("text") or h.get("snippet") or "").strip()
        parts.append(
            f"[{aid}] section={section} | title={h.get('title')}\n"
            f"{text}"
        )
    return "\n\n".join(parts) if parts else "(no context)"


def _rewrite_numeric_cites(text: str, hits: list[dict]) -> str:
    def cite_for(n: int) -> str | None:
        if 1 <= n <= len(hits):
            aid = hits[n - 1].get("arxiv_id")
            if aid:
                return str(aid)
        return None

    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if re.search(r"\d+\.\d+", inner):
            return match.group(0)
        nums = [int(x) for x in re.findall(r"\d+", inner)]
        if not nums:
            return match.group(0)
        seen: list[str] = []
        for n in nums:
            aid = cite_for(n)
            if aid and aid not in seen:
                seen.append(aid)
        if not seen:
            return match.group(0)
        return "".join(f"[{aid}]" for aid in seen)

    return re.sub(r"\[([^\]]+)\]", repl, text)


def generate_answer(question: str, hits: list[dict], *, kind: str = "default") -> str:
    """
    Grounded answer from retrieval hits. Does not write to DB.
    Raises on API failure - caller keeps showing snippets or an error.
    """
    if not hits:
        return "No relevant context found in the indexed library."

    prompt = _PROMPT_THEME if kind == "theme" else _PROMPT
    body = prompt.format(
        question=question.strip(),
        context=_format_context(hits),
    )

    result = generate_content(
        body,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    text = (result.text or "").strip()
    if not text:
        raise ValueError("empty model response")
    return _rewrite_numeric_cites(text, hits)