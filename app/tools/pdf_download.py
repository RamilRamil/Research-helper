import os
from pathlib import Path

import httpx

ARXIV_PDF_DELAY = 3


def pdf_path(arxiv_id: str) -> Path:
    base = Path(os.environ.get("PAPERS_DIR", "data/papers"))
    base.mkdir(parents=True, exist_ok=True)
    clean_id = arxiv_id.split("v")[0]
    return base / f"{clean_id}.pdf"


def download_pdf(arxiv_id: str) -> Path:
    dest = pdf_path(arxiv_id)
    clean_id = dest.stem
    if dest.exists():
        return dest

    url = f"https://arxiv.org/pdf/{clean_id}.pdf"
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        dest.write_bytes(response.content)

    return dest