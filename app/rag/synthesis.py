import json
import os
import re
import time
from collections import defaultdict

from google import genai
from google.genai import types

from app.db.search import hybrid_search
from app.rag.answer import generate_answer

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

GEN_MODEL = "gemini-flash-latest"

_DECOMPOSE_PROMPT = """Split the user question into 2-4 short search subquestions
for a scientific paper library. Focus on distinct aspects to compare or survey.

Return ONLY JSON:
{{"subquestions": ["...", "..."]}}

Question:
{question}
"""

_MAP_PROMPT = """Summarize what THIS paper says that is relevant to the user question.
Use only the excerpts. Cite as [{arxiv_id}]. 3-6 sentences max.
If excerpts are weak, say what is missing.

User question:
{question}

Paper: [{arxiv_id}] {title}

Excerpts:
{excerpts}
"""

_REDUCE_PROMPT = """You write a comparison / synthesis answer across papers.

Rules:
- Use ONLY the per-paper notes below.
- Every claim must cite [arxiv_id].
- Cover multiple papers when notes exist; do not focus on only one.
- If notes conflict, say so.
- Same language as the question when possible.

Question:
{question}

Per-paper notes:
{notes}
"""


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _gen_text(prompt: str, *, json_mode: bool = False) -> str:
    config_kwargs: dict = {"temperature": 0.2}
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            result = client.models.generate_content(
                model=GEN_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = (result.text or "").strip()
            if not text:
                raise ValueError("empty model response")
            return text
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"synthesis LLM failed: {last_err}")


def _heuristic_subquestions(question: str) -> list[str]:
    q = question.strip()
    return [
        q,
        f"methods and approaches related to: {q}",
        f"limitations and differences related to: {q}",
    ]


def decompose_question(question: str) -> list[str]:
    try:
        raw = _gen_text(
            _DECOMPOSE_PROMPT.format(question=question.strip()),
            json_mode=True,
        )
        data = _parse_json(raw)
        subs = data.get("subquestions") or []
        out = [str(s).strip() for s in subs if str(s).strip()]
        if len(out) >= 2:
            return out[:4]
    except Exception:
        pass
    return _heuristic_subquestions(question)


def _group_hits_by_paper(hits: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    seen_chunks: set[str] = set()
    for h in hits:
        cid = str(h.get("chunk_id") or "")
        key = cid or f"{h.get('arxiv_id')}:{str(h.get('snippet') or '')[:40]}"
        if key in seen_chunks:
            continue
        seen_chunks.add(key)
        aid = h.get("arxiv_id")
        if aid:
            grouped[str(aid)].append(h)
    return grouped


def _map_paper(question: str, arxiv_id: str, hits: list[dict]) -> str:
    title = hits[0].get("title") or ""
    excerpts = []
    for h in hits[:4]:
        section = h.get("section") or "?"
        text = (h.get("text") or h.get("snippet") or "").strip()
        excerpts.append(f"({section}) {text}")
    prompt = _MAP_PROMPT.format(
        question=question,
        arxiv_id=arxiv_id,
        title=title,
        excerpts="\n\n".join(excerpts),
    )
    try:
        return _gen_text(prompt, json_mode=False)
    except Exception as e:
        snips = " | ".join(str(h.get("snippet") or "")[:120] for h in hits[:2])
        return f"[{arxiv_id}] {title}. Excerpts: {snips} (map LLM failed: {e})"


def synthesize_answer(
    question: str, *, per_sub_limit: int = 5
) -> tuple[str, list[dict]]:
    """
    Returns (final_answer, hits_for_sources).
    """
    subs = decompose_question(question)
    all_hits: list[dict] = []
    for sub in subs:
        all_hits.extend(hybrid_search(sub, limit=per_sub_limit))

    grouped = _group_hits_by_paper(all_hits)
    if not grouped:
        return "No relevant context found in the indexed library.", []

    notes: list[str] = []
    flat_for_sources: list[dict] = []
    for arxiv_id, hits in list(grouped.items())[:6]:
        notes.append(_map_paper(question, arxiv_id, hits))
        flat_for_sources.extend(hits[:2])

    notes_block = "\n\n---\n\n".join(notes)
    try:
        answer = _gen_text(
            _REDUCE_PROMPT.format(
                question=question.strip(),
                notes=notes_block,
            ),
            json_mode=False,
        )
    except Exception:
        answer = generate_answer(question, flat_for_sources)

    return answer, flat_for_sources