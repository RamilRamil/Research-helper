import os
import time

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-embedding-001"


def embed_text(text: str, *, for_query: bool = False) -> list[float]:
    task = "RETRIEVAL_QUERY" if for_query else "RETRIEVAL_DOCUMENT"
    for attempt in range(3):
        try:
            result = client.models.embed_content(
                model=MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task,
                    output_dimensionality=3072),
            )
            return list(result.embeddings[0].values)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("embed failed")

