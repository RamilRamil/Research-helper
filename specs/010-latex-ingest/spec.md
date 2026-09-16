# Feature Specification: LaTeX-first Ingest Text

**Feature Branch**: `010-latex-ingest`  
**Created**: 2026-09-11  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Rebuild uses e-print text when arXiv source exists (Priority: P1)

As bot owner, when a paper has an arXiv source tarball with TeX, ingest/rebuild
chunks that text instead of PDF layout noise.

**Why this priority**: PDF extract splits headings and formulas; TeX sections
are cleaner for chunking.

**Independent Test**: Rebuild one paper known to have source. Stored fragments
contain TeX section structure (e.g. Introduction as a heading), not only
page-dumped PDF lines.

**Acceptance Scenarios**:

1. **Given** arXiv source contains at least one `.tex` file, **when** ingest or
   staged rebuild extracts text, **then** chunking input is that TeX (comments
   stripped), and the local PDF is still kept on disk.
2. **Given** source is missing or has no `.tex`, **when** extract runs, **then**
   PDF text is used. One extract function chooses the source; not two chunkers.

---

## Requirements

- **FR-001**: Extract MUST prefer arXiv e-print TeX over PDF when `.tex` exists.
- **FR-002**: PDF file MUST remain on the papers volume either way.
- **FR-003**: No GROBID, no new packages.
- **FR-004**: Staged rebuild (009) MUST use this extract.
- **FR-005**: No silent second chunker.

## Success Criteria

- **SC-001**: One rebuilt paper with TeX source shows section-like headings in
  chunks that PDF dump typically mangled.
- **SC-002**: A paper without TeX source still indexes from PDF.

## Assumptions

- Source URL is the existing arXiv e-print endpoint used with `httpx`.
- Comment-stripped concatenation of `.tex` files is enough; no full TeX engine.

## Out of Scope

- Compiling PDF from TeX, GROBID, Leiden, Ragas.
