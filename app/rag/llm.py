import os

import httpx
from google.genai import types

CHAT_MODEL = "deepseek/deepseek-v3.2"
OR_URL = "https://openrouter.ai/api/v1"


class _TextResult:
    def __init__(self, text: str) -> None:
        self.text = text


def _is_capacity_error(exc: BaseException) -> bool:
    text = str(exc)
    return (
        "503" in text
        or "UNAVAILABLE" in text
        or "429" in text
        or "RESOURCE_EXHAUSTED" in text
    )


def _openrouter_key() -> str:
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    return key


def _err_body(text: str) -> str:
    cut = text.find("user_id")
    if cut != -1:
        text = text[:cut]
    return text[:400]


def _openrouter_post(path: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {_openrouter_key()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60.0) as http:
        response = http.post(f"{OR_URL}{path}", headers=headers, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(
                f"openrouter {response.status_code}: {_err_body(response.text)}"
            )
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("openrouter returned non-object JSON")
    return data


def generate_content(contents: str, *, config: types.GenerateContentConfig):
    payload: dict = {
        "model": CHAT_MODEL,
        "messages": [{"role": "user", "content": contents}],
        "temperature": float(getattr(config, "temperature", 0.2) or 0.0),
        "max_tokens": 4096,
    }
    mime = getattr(config, "response_mime_type", None)
    if mime == "application/json":
        payload["response_format"] = {"type": "json_object"}
    data = _openrouter_post("/chat/completions", payload)
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"openrouter chat shape: {e}") from e
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("openrouter empty chat")
    return _TextResult(text)
