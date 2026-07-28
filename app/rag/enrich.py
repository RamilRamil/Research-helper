import json
import os
import re
import time

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# generative model (not embedding)
GEN_MODEL = "gemini-2.0-flash"

_PROMPT = """You enrich a research paper card for a personal library.

Return ONLY valid JSON (no markdown fences) with keys:
- summary_en: string, 2-4 sentences in English
- summary_ru: string, 2-4 sentences in Russian
- tags: array of 3-8 short English tags (topics, methods, domains)

Be factual. Do not invent citations or results not supported by the text.

Title: {title}

Abstract:
{abstract}

Excerpts:
{excerpts}
"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def enrich_paper_card(
    *,
    title: str,
    abstract: str | None,
    excerpts: list[str],
) -> dict:
    """
    Returns dict with summary_en, summary_ru, tags (list[str]).
    Raises on API/parse failure — caller must not change ingest_status.
    """
    body = _PROMPT.format(
        title=title or "(no title)",
        abstract=(abstract or "").strip() or "(no abstract)",
        excerpts="\n\n---\n\n".join(excerpts) if excerpts else "(no excerpts)",
    )

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            result = client.models.generate_content(
                model=GEN_MODEL,
                contents=body,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            data = _parse_json(result.text or "")
            summary_en = str(data.get("summary_en") or "").strip()
            summary_ru = str(data.get("summary_ru") or "").strip()
            tags_raw = data.get("tags") or []
            if not isinstance(tags_raw, list):
                raise ValueError("tags must be a list")
            tags = [str(t).strip() for t in tags_raw if str(t).strip()]
            if not summary_en or not summary_ru:
                raise ValueError("empty summary")
            return {
                "summary_en": summary_en,
                "summary_ru": summary_ru,
                "tags": tags,
            }
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"enrich failed: {last_err}")