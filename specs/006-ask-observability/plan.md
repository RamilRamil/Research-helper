# Implementation Plan: Ask Observability

`app/rag/trace.py`: append JSONL to
`Path(PAPERS_DIR or data/papers) / "_ask_traces.jsonl"`.

`log_ask(record: dict)` swallows OSError.

`cmd_ask` builds a record and `finally: log_ask`.

No compose change. No requirements.txt change.
