import json
import os
import time
from pathlib import Path


def _trace_path() -> Path:
    base = Path(os.environ.get("PAPERS_DIR", "data/papers"))
    return base / "_ask_traces.jsonl"


def log_ask(record: dict) -> None:
    row = dict(record)
    row["ts"] = int(time.time())
    try:
        path = _trace_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    except OSError:
        return
