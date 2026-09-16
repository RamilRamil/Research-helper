from app.rag.answer import generate_answer
from app.rag.router import plan_query
from app.rag.synthesis import synthesize_answer


def run_ask(question: str) -> dict:
    rec: dict = {
        "question": question[:500],
        "route": "",
        "tool": "",
        "outcome": "unknown",
        "n_hits": 0,
        "arxiv_ids": [],
        "error": "",
        "answer": None,
        "hits": [],
    }
    hits: list = []
    answer: str | None = None
    try:
        plan = plan_query(question)
        rec["route"] = plan["route"]
        rec["tool"] = plan["tool"]
        mode = plan["route"]
        tool = plan["tool"]

        if mode == "synthesis":
            answer, hits = synthesize_answer(question)
        elif mode == "graph":
            from app.rag.crag import is_grounded
            from app.rag.graph import retrieve_graph

            hits = retrieve_graph(question)
            if not hits:
                rec["outcome"] = "refuse_support"
                rec["answer"] = "Indexed library cannot support this question."
                rec["hits"] = hits
                return rec
            answer = generate_answer(question, hits, kind="theme")
            if not is_grounded(question, answer, hits, kind="theme"):
                rec["outcome"] = "refuse_grounded"
                rec["n_hits"] = len(hits)
                rec["hits"] = hits
                rec["answer"] = answer
                rec["arxiv_ids"] = _ids(hits)
                return rec
        else:
            from app.rag.crag import is_grounded, retrieve_with_correction

            hits = retrieve_with_correction(question, tool)
            if not hits:
                rec["outcome"] = "refuse_support"
                rec["answer"] = "Indexed library cannot support this question."
                rec["hits"] = hits
                return rec
            answer = generate_answer(question, hits)
            if not is_grounded(question, answer, hits):
                rec["outcome"] = "refuse_grounded"
                rec["n_hits"] = len(hits)
                rec["hits"] = hits
                rec["answer"] = answer
                rec["arxiv_ids"] = _ids(hits)
                return rec

        rec["n_hits"] = len(hits)
        rec["arxiv_ids"] = _ids(hits)
        rec["hits"] = hits
        rec["answer"] = answer

        if answer == "Indexed library cannot support this question.":
            rec["outcome"] = "refuse_support"
            return rec
        if not answer:
            rec["outcome"] = "refuse_support"
            rec["answer"] = "No relevant chunks found"
            return rec
        rec["outcome"] = "answered"
        return rec
    except Exception as e:
        rec["outcome"] = "error"
        rec["error"] = str(e)[:300]
        rec["n_hits"] = len(hits)
        rec["hits"] = hits
        rec["answer"] = answer
        rec["arxiv_ids"] = _ids(hits)
        return rec


def _ids(hits: list) -> list[str]:
    out: list[str] = []
    for h in hits:
        aid = h.get("arxiv_id")
        if aid and aid not in out:
            out.append(aid)
    return out
