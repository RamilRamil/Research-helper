# Spec Kit features

Governance: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md).
Strategy map: [`../RAG_UPGRADE_PLAN.md`](../RAG_UPGRADE_PLAN.md).

Active feature is in `.specify/feature.json`.

| Directory | Status |
|-----------|--------|
| [001-stabilize-rag-ingest](./001-stabilize-rag-ingest/) | Verified |
| [002-two-stage-rerank](./002-two-stage-rerank/) | Live `/ask` ok |
| [003-semantic-chunking](./003-semantic-chunking/) | Live reindex ok |
| [004-crag-self-rag](./004-crag-self-rag/) | Grade, rewrite, groundedness |
| [005-query-routing](./005-query-routing/) | LLM point/synthesis |
| [006-ask-observability](./006-ask-observability/) | JSONL traces |
| [007-paper-graph](./007-paper-graph/) | Live graph ok |
| [008-cite-and-neighbors](./008-cite-and-neighbors/) | Cite arXiv ids; category hop if tags empty |
| [009-staged-reindex](./009-staged-reindex/) | Drain done: all 32 indexed on live chunk_gen |
| [010-latex-ingest](./010-latex-ingest/) | TeX extract live; T002 ok on 2607.18826 |
| [011-leiden-communities](./011-leiden-communities/) | Verified. Graph `/ask` Sources from 5 papers (agent memory). |
| [012-ragas-eval](./012-ragas-eval/) | Verified. `data/papers/_ragas_eval.json`: graph ask scored; weather refuse_support explicit. |
| [013-graph-faithfulness](./013-graph-faithfulness/) | Verified. Graph eval faithfulness 0.91; 5 sources; weather refuse. |
| [014-embed-quota-fail](./014-embed-quota-fail/) | Verified. Gemini embed only; quota fails closed. |
| [015-deepseek-chat](./015-deepseek-chat/) | Verified. Chat `deepseek/deepseek-v3.2`; embed Gemini. |
| [016-supply-chain-pins](./016-supply-chain-pins/) | Verified. 117 exact pins; rebuild ok. |
| [017-mcp-library-server](./017-mcp-library-server/) | Verified. Local read-only stdio: list/get/search. |
| [018-mcp-http-auth](./018-mcp-http-auth/) | Verified. Streamable HTTP + Bearer `MCP_TOKEN` + per-IP rate limit; stdio intact. |
