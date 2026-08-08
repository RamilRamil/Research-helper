import re

# point = single-paper / factual; synthesis = compare / survey across papers
_SYNTHESIS_PATTERNS = [
    r"\bcompar(e|ison|ing)\b",
    r"\bdiffer(ence|ences|ent)?\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\ball papers\b",
    r"\bacross (papers|works|methods)\b",
    r"\bwhich approaches?\b",
    r"\bwhat approaches?\b",
    r"\bsurvey\b",
    r"\boverview\b",
    r"\bсравни",
    r"\bотлича",
    r"\bразниц",
    r"\bчем отлича",
    r"\bкакие подходы",
    r"\bвсе статьи",
    r"\bмежду стать",
]


def route_question(question: str) -> str:
    """
    Return 'point' or 'synthesis'.
    Heuristic only — no API calls.
    """
    q = (question or "").strip().lower()
    if not q:
        return "point"
    for pat in _SYNTHESIS_PATTERNS:
        if re.search(pat, q, flags=re.IGNORECASE):
            return "synthesis"
    return "point"