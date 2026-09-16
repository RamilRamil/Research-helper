# Section evaluation (001)

**Date:** 2026-09-09  
**Method:** SQL `chunks.section` for five indexed papers; same IDs re-extracted with
`pdf_extract` + `chunker.split_sections` in the app image (PyMuPDF).

## T025

19 `indexed` papers in DB. 32+ PDFs on disk. Sampled:

- 2604.16548
- 2605.04050
- 2605.23723
- 2607.05120
- 2607.22301

## Stored labels vs live split

| arxiv_id | Stored sections (counts) | Live split names |
|----------|--------------------------|------------------|
| 2604.16548 | Introduction 41, References 25, Appendix 5, Abstract 2, Preamble 1 | Preamble, Abstract, Introduction, References, Appendix |
| 2605.04050 | Introduction 26, References 11, Results 7, Conclusion 3, Evaluation 2, Abstract 2, Preamble 1 | Preamble, Abstract, Introduction, Evaluation, Results, Conclusion, References |
| 2605.23723 | References 30, Related Work 17, Results 11, Introduction 7, Conclusion 4, Abstract 2, Preamble 1 | Preamble, Abstract, Introduction, Related Work, Results, Conclusion, References |
| 2607.05120 | NULL x 120 | Preamble, Introduction, Background, Evaluation, Conclusion, References |
| 2607.22301 | Introduction 21, References 3, Preamble 2 | Preamble, Introduction, References |

`2607.05120` stored chunks predate section fill (all NULL). Live regex sees numbered
headings (`1. Introduction`, `2. Background`, ...). Not a reason to switch ingest to
LaTeX-first; it is a stale-index issue (needs explicit `/reindex` later, which 001
forbids on `indexed` until staged reindex).

Heavy `References` share is expected (long bib windowed at 1000/200).

Missed vs typical paper: Methods/Approach often absent from `SECTION_NAMES` or not
line-isolated in PDF text. Sampled papers still got Abstract/Introduction/Conclusion
when the PDF lines matched the regex.

## Decision

**Retain PDF-first** section regex. Do **not** open a LaTeX-first spec from this
sample. Optional later: staged reindex for rows with NULL `section` (new spec).
