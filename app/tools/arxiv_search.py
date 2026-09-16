from datetime import date, timedelta

import arxiv
import re


def parse_terms(topic: str) -> list[str]:
    terms = []
    for m in re.finditer(r'"([^"]+)"|(\S+)', topic):
        if m.group(1):
            terms.append(f'all:"{m.group(1)}"')
        else:
            terms.append(f'all:"{m.group(2)}"')
    return terms


def build_query(topic: str, days: int = 365) -> str:
    date_to = date.today()
    date_from = date_to - timedelta(days=days)
    d0 = date_from.strftime("%Y%m%d")
    d1 = date_to.strftime("%Y%m%d")
    date_part = f"submittedDate:[{d0} TO {d1}]"
    topic_part = " AND ".join(parse_terms(topic))
    return f"({date_part}) AND ({topic_part})"


def search_papers(topic:str, days: int = 365, max_results: int = 10) -> list[dict]:
    query = build_query(topic, days)
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    papers = []
    for item in client.results(search):
        arxiv_id = item.entry_id.split("/abs/")[-1]
        papers.append({
            "arxiv_id": arxiv_id,
            "title": item.title.replace("\n", " "),
            "published": item.published.date().isoformat(),
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "abstract": item.summary.replace("\n", " "),
            "authors": [a.name for a in item.authors],
            "pdf_url": item.pdf_url,
            "categories": list(item.categories or []),
        })
    return papers


def fetch_categories_by_ids(arxiv_ids: list[str]) -> dict[str, list[str]]:
    ids = [a.split("v")[0] for a in arxiv_ids if a]
    out: dict[str, list[str]] = {}
    if not ids:
        return out
    client = arxiv.Client()
    chunk = 20
    for i in range(0, len(ids), chunk):
        batch = ids[i : i + chunk]
        search = arxiv.Search(id_list=batch)
        for item in client.results(search):
            aid = item.entry_id.split("/abs/")[-1].split("v")[0]
            out[aid] = list(item.categories or [])
    return out


def backfill_missing_categories() -> int:
    from app.db.papers import list_arxiv_ids_missing_categories, set_paper_categories

    missing = list_arxiv_ids_missing_categories()
    cats = fetch_categories_by_ids(missing)
    n = 0
    for aid, values in cats.items():
        if not values:
            continue
        set_paper_categories(aid, values)
        n += 1
    return n