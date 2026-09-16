# Plan

Remove OpenRouter from `embed_text`. Gemini `gemini-embedding-001` 3072 only.

On quota/capacity: raise `RuntimeError` mentioning embed quota. Do not retry
into another vendor.

Keep `_openrouter_generate` for chat (already approved, same Gemini family).

Delete `openrouter_embed` and `OR_EMBED`.
