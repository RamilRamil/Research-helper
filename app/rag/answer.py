import os
import time

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

GEN_MODEL = "gemini-flash-latest"

_PROMPT = """You answer a research question using ONLY the context chunks below.

Rules:
- Every factual claim must cite sources as [arxiv_id] using ids from the context.
- If several chunks support a claim, you may write [id1][id2].
- If the context is insufficient, say so clearly. Do not invent papers or results.
- Prefer concise answers (short paragraphs or bullets).
- You may answer in the same language as the question.

Question:
{question}

Context:
{context}
"""


def _format_context(hits: list[dict]) -> str:
    parts = []
    for i, h in enumerate(hits, 1):
        section = h.get("section") or "?"
        text = (h.get("text") or h.get("snippet") or "").strip()
        parts.append(
            f"[{i}] arxiv_id={h.get('arxiv_id')} | section={section} | title={h.get('title')}\n"
            f"{text}"
        )
    return "\n\n".join(parts) if parts else "(no context)"


def generate_answer(question: str, hits: list[dict]) -> str:
    """
    Grounded answer from retrieval hits. Does not write to DB.
    Raises on API failure — caller keeps showing snippets or an error.
    """
    if not hits:
        return "No relevant context found in the indexed library."

    body = _PROMPT.format(
        question=question.strip(),
        context=_format_context(hits),
    )

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            result = client.models.generate_content(
                model=GEN_MODEL,
                contents=body,
                config=types.GenerateContentConfig(temperature=0.2),
            )
            text = (result.text or "").strip()
            if not text:
                raise ValueError("empty model response")
            return text
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"generate_answer failed: {last_err}")