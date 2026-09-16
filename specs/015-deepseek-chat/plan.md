# Plan

`generate_content` calls OpenRouter only, model `deepseek/deepseek-v3.2`.
Drop Gemini generate loop and `GEN_MODELS` / `OR_CHAT` maps.

Keep `types.GenerateContentConfig` at the call sites (temperature, JSON
mime). Embed stays in `embedder.py`.

Eval judge uses the same `CHAT_MODEL` constant.
