from pathlib import Path

import fitz


def extract_text(pdf_file: Path, max_pages: int = 100) -> tuple[str, int]:
    doc = fitz.open(pdf_file)
    pages = min(len(doc), max_pages)
    parts = []
    for i in range(pages):
        parts.append(doc.load_page(i).get_text())
    doc.close()
    text = "\n".join(parts).replace("\x00", "")
    return text, pages