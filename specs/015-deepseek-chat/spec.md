# Feature Specification: DeepSeek V3.2 Chat

**Feature Branch**: `015-deepseek-chat`  
**Created**: 2026-09-16  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Cheap grounded answers (Priority: P1)

As bot owner, `/ask` and other chat steps use one inexpensive chat
model. Embeddings stay on the existing Gemini vector model.

**Why this priority**: Gemini Flash Latest chat is too expensive; owner
chose DeepSeek V3.2.

**Independent Test**: One `/ask` or eval `run_ask` returns a grounded
answer or an explicit refuse. No Gemini chat model id in the generate
path.

**Acceptance Scenarios**:

1. **Given** OpenRouter is configured, **when** the bot generates an
   answer, **then** the chat model is DeepSeek V3.2.
2. **Given** OpenRouter is missing or chat fails, **when** generate is
   called, **then** the error is explicit; Gemini chat is not used as a
   backup.

---

## Requirements

- **FR-001**: Live generate (answer, router, rerank, CRAG, enrich,
  eval judge) MUST use DeepSeek V3.2 via the existing OpenRouter
  chat path.
- **FR-002**: Embed MUST remain Gemini 3072.
- **FR-003**: MUST NOT fall back to Gemini Flash (or any second chat
  family) on quota or error.
- **FR-004**: No new libraries.

## Success Criteria

- **SC-001**: A supported library question still produces an answer
  with source paper ids, or a refuse, using the new chat model.
- **SC-002**: Code search for generate shows one chat model id.

## Assumptions

- Owner-approved replacement of Gemini for generate only.
- Slug `deepseek/deepseek-v3.2` on OpenRouter.

## Out of Scope

- Supply-chain pins, MCP, ACL, embed vendor change.
