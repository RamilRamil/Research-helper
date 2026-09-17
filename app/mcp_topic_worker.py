"""Worker: drain mcp_topic_jobs (search + ingest + enrich)."""

from __future__ import annotations

import time

from dotenv import load_dotenv

load_dotenv()

from app.db.mcp_topic_jobs import (  # noqa: E402
    claim_next_queued,
    mark_failed,
    mark_succeeded,
)
from app.db.papers import get_paper_status, save_paper  # noqa: E402
from app.tools.arxiv_search import build_query, search_papers  # noqa: E402
from app.tools.enrich_paper import enrich_and_save  # noqa: E402
from app.tools.ingest_paper import IngestBusyError, ingest_paper  # noqa: E402

_IDLE_SLEEP_SEC = 2.0
_BUSY_RETRIES = 3


def _clean_id(arxiv_id: str) -> str:
    return arxiv_id.split("v")[0]


def _run_job(job_id: int, topic: str) -> None:
    try:
        papers = search_papers(topic, days=365, max_results=10)
    except Exception as exc:
        mark_failed(job_id, f"search failed: {exc}")
        return

    found = len(papers)
    indexed = 0
    failed = 0
    search_query = build_query(topic)

    for paper in papers:
        clean = _clean_id(paper["arxiv_id"])
        try:
            save_paper(paper, topic, search_query)
            status = get_paper_status(clean)
            if status == "indexed":
                continue
            if status is None:
                failed += 1
                continue
            ok = False
            for attempt in range(_BUSY_RETRIES):
                try:
                    ingest_paper(clean)
                    ok = True
                    break
                except IngestBusyError:
                    if attempt + 1 >= _BUSY_RETRIES:
                        break
                    time.sleep(2.0)
                except Exception:
                    ok = False
                    break
            if not ok:
                failed += 1
                continue
            try:
                enrich_and_save(clean)
            except Exception:
                pass
            if get_paper_status(clean) == "indexed":
                indexed += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    mark_succeeded(
        job_id,
        found_count=found,
        indexed_count=indexed,
        failed_count=failed,
    )


def run_forever() -> None:
    while True:
        job = claim_next_queued()
        if job is None:
            time.sleep(_IDLE_SLEEP_SEC)
            continue
        try:
            _run_job(job.id, job.topic)
        except Exception as exc:
            try:
                mark_failed(job.id, f"worker crashed: {exc}")
            except Exception:
                pass


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
