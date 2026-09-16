import json
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI
import instructor
from ragas.llms.base import InstructorLLM
from ragas.metrics.collections import (
    ContextPrecisionWithoutReference,
    Faithfulness,
)

from app.rag.ask import run_ask
from app.rag.llm import CHAT_MODEL

JUDGE_MODEL = CHAT_MODEL


async def _agenerate_via_generate(self, prompt: str, response_model):
    return self.generate(prompt, response_model)


InstructorLLM.agenerate = _agenerate_via_generate


def _questions() -> list[str]:
    path = Path("specs/012-ragas-eval/questions.txt")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def _contexts(hits: list) -> list[str]:
    out = []
    for h in hits:
        text = (h.get("text") or h.get("snippet") or "").strip()
        if text:
            out.append(text)
    return out


def _num(value) -> float | None:
    if value is None:
        return None
    n = float(value)
    if math.isnan(n):
        return None
    return n


def _score_row(question: str, rec: dict, faith: Faithfulness, prec: ContextPrecisionWithoutReference) -> dict:
    row = {
        "question": question,
        "outcome": rec.get("outcome"),
        "route": rec.get("route"),
        "arxiv_ids": rec.get("arxiv_ids") or [],
        "error": rec.get("error") or "",
        "faithfulness": None,
        "context_precision": None,
    }
    answer = rec.get("answer") or ""
    ctx = _contexts(rec.get("hits") or [])
    if not answer or not ctx:
        if not row["error"]:
            row["error"] = rec.get("outcome") or "no answer or contexts"
        return row
    scored = faith.score(
        user_input=question, response=answer, retrieved_contexts=ctx
    )
    pscored = prec.score(
        user_input=question, response=answer, retrieved_contexts=ctx
    )
    fv, pv = scored.value, pscored.value
    row["faithfulness"] = _num(fv)
    row["context_precision"] = _num(pv)
    return row


def _err(exc: BaseException) -> str:
    text = str(exc)
    cut = text.find("user_id")
    if cut != -1:
        text = text[:cut]
    return text[:400]


def _judge_llm():
    key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing for ragas judge")
    raw = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    patched = instructor.from_openai(raw, mode=instructor.Mode.JSON)
    return InstructorLLM(
        client=patched,
        model=JUDGE_MODEL,
        provider="openai",
        max_tokens=8192,
    )


def main() -> None:
    llm = _judge_llm()
    faith = Faithfulness(llm=llm)
    prec = ContextPrecisionWithoutReference(llm=llm)

    rows = []
    for q in _questions():
        rec = run_ask(q)
        try:
            rows.append(_score_row(q, rec, faith, prec))
        except Exception as e:
            rows.append(
                {
                    "question": q,
                    "outcome": rec.get("outcome"),
                    "route": rec.get("route"),
                    "arxiv_ids": rec.get("arxiv_ids") or [],
                    "error": _err(e),
                    "faithfulness": None,
                    "context_precision": None,
                }
            )

    out = {
        "ts": int(time.time()),
        "judge": JUDGE_MODEL,
        "rows": rows,
    }
    dest = Path(os.environ.get("PAPERS_DIR", "data/papers")) / "_ragas_eval.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
    print(dest)
    print(json.dumps(out, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
