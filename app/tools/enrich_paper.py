from app.db.papers import get_enrichment_input, save_paper_enrichment
from app.rag.enrich import enrich_paper_card


def enrich_and_save(arxiv_id: str) -> dict:
    """
    Build card via Gemini and persist summaries/tags.
    Does not modify ingest_status.
    """
    inp = get_enrichment_input(arxiv_id)
    card = enrich_paper_card(
        title=inp["title"],
        abstract=inp["abstract"],
        excerpts=inp["excerpts"],
    )
    save_paper_enrichment(
        inp["arxiv_id"],
        summary_en=card["summary_en"],
        summary_ru=card["summary_ru"],
        tags=card["tags"],
    )
    return card