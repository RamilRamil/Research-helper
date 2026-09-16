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

_SECTION_RE = re.compile(
    r"(?im)^(?:\d+(?:\.\d+)*\.?\s+)?("
    + "|".join(re.escape(n) for n in SECTION_NAMES)
    + r")\s*$"
)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _hard_cut(text: str) -> list[str]:
    out = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        if end < n:
            sp = text.rfind(" ", start, end)
            if sp > start:
                end = sp
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        if end >= n:
            break
        start = end
        while start < n and text[start].isspace():
            start += 1
    return out or ([text.strip()] if text.strip() else [])


def _units(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    units: list[str] = []
    for para in paras:
        p = para.strip()
        if not p:
            continue
        if len(p) <= CHUNK_SIZE:
            units.append(p)
            continue
        bits = [b.strip() for b in _SENTENCE_RE.split(p) if b.strip()]
        if not bits:
            units.extend(_hard_cut(p))
            continue
        for b in bits:
            if len(b) <= CHUNK_SIZE:
                units.append(b)
            else:
                units.extend(_hard_cut(b))
    return units


def _overlap_prefix(packed: list[str]) -> list[str]:
    if not packed:
        return []
    acc: list[str] = []
    total = 0
    for u in reversed(packed):
        acc.insert(0, u)
        total += len(u) + (1 if total else 0)
        if total >= CHUNK_OVERLAP:
            break
    joined = " ".join(acc)
    if len(joined) > CHUNK_SIZE:
        return packed[-1:]
    return acc


def _pack_units(units: list[str]) -> list[str]:
    if not units:
        return []
    chunks: list[str] = []
    packed: list[str] = []

    def packed_len(parts: list[str]) -> int:
        if not parts:
            return 0
        return len(" ".join(parts))

    for u in units:
        if packed and packed_len(packed + [u]) > CHUNK_SIZE:
            chunks.append(" ".join(packed))
            packed = _overlap_prefix(packed)
            if packed_len(packed + [u]) > CHUNK_SIZE:
                packed = []
        packed.append(u)
    if packed:
        chunks.append(" ".join(packed))
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
            for part in _pack_units(_units(body)):
                if part.strip():
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
