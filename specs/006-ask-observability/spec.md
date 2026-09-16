# Feature Specification: Ask Observability

**Feature Branch**: `006-ask-observability`  
**Created**: 2026-09-10  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Each /ask leaves an inspectable record (Priority: P1)

As bot owner, after `/ask` I can see what route ran, whether the bot refused,
and which paper ids were in the evidence set, without guessing from Telegram
wording.

**Why this priority**: 004/005 failures were opaque (rerank error vs refuse).
Need traces before GraphRAG.

**Independent Test**: Run one `/ask`. A new JSON line exists with the question,
route, outcome, and source arXiv ids (or empty on refuse).

**Acceptance Scenarios**:

1. **Given** a successful `/ask`, **when** the turn ends, **then** a trace
   records `answered` and the source ids.
2. **Given** CRAG refuse, **when** the turn ends, **then** a trace records
   `refuse_support` (or equivalent) and not `answered`.
3. **Given** a router/API error, **when** the turn ends, **then** a trace
   records `error` plus a short error string without secrets.

---

### User Story 2 - No Ragas package in this feature (Priority: P1)

As bot owner, observability ships without a new eval framework dependency.

**Acceptance Scenarios**:

1. **Given** this feature, **when** `requirements.txt` is inspected, **then**
   Ragas (and similar) are not added.

---

## Requirements

- **FR-001**: System MUST append one JSON object per `/ask` attempt to a file
  on the existing papers volume (no new top-level directory).
- **FR-002**: Record MUST include question (truncated), route, tool, outcome,
  hit count, arXiv ids, unix timestamp. MUST NOT include API keys.
- **FR-003**: Outcomes MUST distinguish answered, support-refuse,
  groundedness-refuse, and error.
- **FR-004**: Tracing MUST NOT change answer text. If the log write fails,
  `/ask` still completes; the user is not blocked on disk errors.
- **FR-005**: No new Python packages. Automated Ragas CI is a later spec.

## Success Criteria

- **SC-001**: After one `/ask`, the trace file gains exactly one new line for
  that turn.
- **SC-002**: `requirements.txt` unchanged for this feature.

## Assumptions

- File lives beside PDFs so Docker bind-mount persists it.
- Full faithfulness/precision dashboards wait for an approved eval library.

## Out of Scope

- GraphRAG, Langfuse, Ragas install, Telegram dump of full traces.
