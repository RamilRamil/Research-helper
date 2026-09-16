# Implementation Plan: Semantic Adaptive Chunking

## Technical Context

| Area | Current | Change |
|------|---------|--------|
| Chunker | section + char window 1000/200 | pack paragraph/sentence units to 1000, overlap last unit(s) up to ~200 |
| Indexed rows | immutable on `/search` | no change |
| Reindex incomplete | deletes/recreates chunks | gets new packer automatically |
| Deps | none | none |

## Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| One pillar | Pass | chunking only |
| Indexed immutable | Pass | no bulk reindex |
| No new libs | Pass | stdlib regex |
| No dual chunkers | Pass | replace `_window_chunks`, one path |
| No MCPD Gemini | Pass | deferred |

## Design

Keep `split_sections`. Replace `_window_chunks`:

1. Split section body on blank lines into paragraphs.
2. If a paragraph is still longer than `CHUNK_SIZE`, split on `(?<=[.!?])\s+`.
3. If a unit is still longer, hard-cut that unit only (one unsplittable blob).
4. Greedy pack units into chunks `<= CHUNK_SIZE`.
5. Overlap: start the next chunk with the smallest suffix of packed units whose
   joined length is `>= CHUNK_OVERLAP` and `<= CHUNK_SIZE`, else the last unit.

One function path. No second window algorithm left in the file.

## Files

| File | Change |
|------|--------|
| `app/rag/chunker.py` | packer |
| `specs/003-semantic-chunking/` | notes after a dry `chunk_text` on one PDF in app image |

## Deferred

LLM/MCPD chunking; staged reindex of `indexed`.
