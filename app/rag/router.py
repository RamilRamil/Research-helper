import json
import re

from google.genai import types

from app.rag.llm import generate_content

_PROMPT = """Classify the user question for a scientific paper library.

Return ONLY JSON:
{{"route": "point", "tool": "hybrid"}}

route:
- point: one fact, one paper, or an arXiv id
- synthesis: compare, survey, or contrast several named methods
- graph: themes across the library, related papers, what the collection covers

tool (only for point):
- hybrid: default dense plus full-text
- fts: exact id, code, or rare token

Question:
{question}
"""


def _parse(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("router expected JSON object")
    return data


def plan_query(question: str) -> dict:
    q = (question or "").strip()
    if not q:
        return {"route": "point", "tool": "hybrid"}
    from app.rag.rerank import parse_arxiv_id

    if parse_arxiv_id(q):
        return {"route": "point", "tool": "hybrid"}
    result = generate_content(
        _PROMPT.format(question=q),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    data = _parse(result.text or "")
    route = str(data.get("route") or "").strip().lower()
    if route not in ("point", "synthesis", "graph"):
        raise ValueError(f"invalid route: {route}")
    tool = str(data.get("tool") or "hybrid").strip().lower()
    if tool not in ("hybrid", "fts"):
        tool = "hybrid"
    if route in ("synthesis", "graph"):
        tool = "hybrid"
    return {"route": route, "tool": tool}


def route_question(question: str) -> str:
    return plan_query(question)["route"]
