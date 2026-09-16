import io
import tarfile
from pathlib import Path

import fitz
import httpx


def extract_text(pdf_file: Path, max_pages: int = 100) -> tuple[str, int]:
    doc = fitz.open(pdf_file)
    pages = min(len(doc), max_pages)
    parts = []
    for i in range(pages):
        parts.append(doc.load_page(i).get_text())
    doc.close()
    text = "\n".join(parts).replace("\x00", "")
    return text, pages


def _strip_tex_comments(src: str) -> str:
    out = []
    for line in src.splitlines():
        if line.lstrip().startswith("%"):
            continue
        cut = []
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            cut.append(line[i])
            i += 1
        out.append("".join(cut).rstrip())
    return "\n".join(out)


def _tex_from_eprint(arxiv_id: str) -> str:
    clean = arxiv_id.split("v")[0]
    url = f"https://arxiv.org/e-print/{clean}"
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code >= 400:
            return ""
        blob = response.content
    try:
        tar = tarfile.open(fileobj=io.BytesIO(blob), mode="r:*")
    except tarfile.TarError:
        return ""
    parts: list[str] = []
    for member in sorted(tar.getmembers(), key=lambda m: m.name):
        if not member.isfile() or not member.name.lower().endswith(".tex"):
            continue
        extracted = tar.extractfile(member)
        if extracted is None:
            continue
        raw = extracted.read().decode("utf-8", errors="replace")
        parts.append(_strip_tex_comments(raw))
    tar.close()
    return "\n\n".join(p for p in parts if p.strip())


def extract_paper(arxiv_id: str, pdf_file: Path, max_pages: int = 100) -> tuple[str, int]:
    pdf_text, pages = extract_text(pdf_file, max_pages=max_pages)
    tex = _tex_from_eprint(arxiv_id)
    if len(tex) >= 500:
        return tex.replace("\x00", ""), pages
    return pdf_text, pages
