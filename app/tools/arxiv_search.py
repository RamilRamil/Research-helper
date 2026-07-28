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


def build_query(topic: str, days: int = 30) -> str:
    date_to = date.today()
    date_from = date_to - timedelta(days=days)
    d0 = date_from.strftime("%Y%m%d")
    d1 = date_to.strftime("%Y%m%d")
    date_part = f"submittedDate:[{d0} TO {d1}]"
    topic_part = " AND ".join(parse_terms(topic))
    return f"({date_part}) AND ({topic_part})"


def search_papers(topic:str, days: int = 30, max_results: int = 10) -> list[dict]:
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
        })
    return papers