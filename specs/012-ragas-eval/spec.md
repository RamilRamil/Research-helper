# Feature Specification: Ragas Eval on Ask Traces

**Feature Branch**: `012-ragas-eval`  
**Created**: 2026-09-11  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Owner can score a fixed ask set (Priority: P1)

As bot owner, I run an eval over listed questions and get faithfulness /
context precision style scores, not vibes.

**Why this priority**: constitution VII.

**Independent Test**: Run eval once. A file of numeric scores exists for each
listed question.

**Acceptance Scenarios**:

1. **Given** a small fixed question list and indexed library, **when** eval
   runs, **then** each question has numeric metric values written to disk.
2. **Given** eval fails on one question, **when** the run ends, **then** other
   questions still have scores; the failure is recorded.

---

## Requirements

- **FR-001**: MUST use Ragas (owner-approved library) on a checked-in question
  list.
- **FR-002**: MUST reuse the live `/ask` retrieve+generate path, not a second
  RAG stack.
- **FR-003**: MUST write scores under the papers data dir.
- **FR-004**: No GitHub Actions in this slice unless already present.

## Success Criteria

- **SC-001**: One eval run produces scores for at least three questions.
- **SC-002**: A question the library cannot support is scored or marked failed
  explicitly, not silently skipped as success.

## Assumptions

- Gemini remains the LLM backend for Ragas where an LLM is required.
- Question list includes `/ask 2607.20124` and one unanswerable weather item.

## Out of Scope

- Full CI gate, Leiden, LaTeX.
