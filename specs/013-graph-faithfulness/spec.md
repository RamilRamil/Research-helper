# Feature Specification: Graph Ask Faithfulness

**Feature Branch**: `013-graph-faithfulness`  
**Created**: 2026-09-16  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Theme answers stay inside retrieved papers (Priority: P1)

As bot owner, when I ask a corpus/theme question, the answer's claims
match the retrieved passages, not a free-form survey.

**Why this priority**: constitution IV and VII. Eval already showed a
supported graph answer with weak faithfulness.

**Independent Test**: Re-run the checked-in eval question on LLM agent
memory. Faithfulness is above the floor. Refuse cases stay refuse.

**Acceptance Scenarios**:

1. **Given** the indexed library and the graph question from the eval
   list, **when** `/ask` answers, **then** each claim is supported by
   the same passages shown as sources.
2. **Given** a question the library cannot support, **when** `/ask`
   runs, **then** the bot still refuses; it does not invent themes to
   raise a score.

---

## Requirements

- **FR-001**: Graph/theme answers MUST be entailed by the retrieved
  passages that the user-facing sources come from.
- **FR-002**: Community labels/summaries MUST NOT become extra "facts"
  in the answer unless those strings are themselves retrieved passages
  for that question.
- **FR-003**: Eval MUST score the graph eval question with the same
  passage texts the answerer used (no silent shorter slice).
- **FR-004**: MUST reuse live `/ask` retrieve+generate. No second RAG
  stack. No new libraries.

## Success Criteria

- **SC-001**: On the checked-in graph eval question, faithfulness is at
  least 0.60 and context precision is not below the previous recorded
  run (0.99).
- **SC-002**: Tokyo weather still fails explicitly (refuse), not as a
  scored success.
- **SC-003**: Graph answers that cite papers still list more than one
  source when the community hop finds them (do not "fix" faithfulness
  by collapsing to one paper).

## Assumptions

- Question list stays `specs/012-ragas-eval/questions.txt`.
- Judge path stays the existing eval script.
- Floor 0.60 is a bar over the recorded 0.23, not a claim of perfect
  extractive QA.

## Out of Scope

- OpenRouter embed quota, supply-chain pins, MCP, ACL.
- Entity-level graph.
- Changing hybrid retrieve for point questions.
