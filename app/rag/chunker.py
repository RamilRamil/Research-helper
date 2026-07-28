import hashlib
import re

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

SECTION_NAMES = [
    "Abstract",
    "Introduction",
    "Related Work",
    "Background",
    "Method",
    "Methods",
    "Approach",
    "Experiment",
    "Experiments",
    "Evaluation",
    "Result",
    "Results",
    "Discussion",
    "Conclusion",
    "Conclusions",
    "References",
    "Bibliography",
    "Appendix",
]

# строка целиком = заголовок: опциональный номер + имя
_SECTION_RE = re.compile(
    r"(?im)^(?:\d+(?:\.\d+)*\.?\s+)?("
    + "|".join(re.escape(n) for n in SECTION_NAMES)
    + r")\s*$"
)


def _window_chunks(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - CHUNK_OVERLAP
    return chunks


def chunk_text(text: str) -> list[dict]:
    sections = split_sections(text)
    out: list[dict] = []
    for sec in sections:
        body = sec["text"].strip()
        if not body:
            continue
        if len(body) <= CHUNK_SIZE:
            out.append({"text": body, "section": sec["section"]})
        else:
            for part in _window_chunks(body):
                out.append({"text": part, "section": sec["section"]})
    return out


def split_sections(text: str) -> list[dict]:
    lines = text.splitlines()
    sections: list[dict] = []
    current_name = "Preamble"
    current_lines: list[str] = []

    def flush():
        body = "\n".join(current_lines).strip()
        if body:
            sections.append({"section": current_name, "text": body})

    for line in lines:
        match = _SECTION_RE.match(line.strip())
        if match:
            flush()
            current_name = match.group(1)
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return sections


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()