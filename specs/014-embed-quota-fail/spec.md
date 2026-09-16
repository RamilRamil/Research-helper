# Feature Specification: Embed Quota Fail Loud

**Feature Branch**: `014-embed-quota-fail`  
**Created**: 2026-09-16  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Quota does not switch embedding space (Priority: P1)

As bot owner, when the embedding provider is out of quota, ingest/search
fails loudly. The index is not filled with vectors from a different model.

**Why this priority**: constitution V. OpenRouter has no Gemini embedding
id; the old second path was a dead lie.

**Independent Test**: Code search shows one embed model. A capacity error
does not call a second embedding API.

**Acceptance Scenarios**:

1. **Given** Gemini embed succeeds, **when** a paper is indexed, **then**
   vectors are still 3072 from the same embedding model as before.
2. **Given** Gemini embed returns quota/capacity, **when** embed is
   requested, **then** the call fails with an explicit quota error and
   does not write vectors from another vendor.

---

## Requirements

- **FR-001**: There MUST be exactly one embedding model in the live path.
- **FR-002**: Quota/capacity on that model MUST fail closed (no second
  embedder, no dimension-incompatible substitute).
- **FR-003**: Chat generate via the already-approved OpenRouter Gemini
  alias is unchanged.
- **FR-004**: No new libraries.

## Success Criteria

- **SC-001**: After a quota-class embed failure, no new chunk vectors are
  stored from a fallback model.
- **SC-002**: Owner can tell from the error that embedding quota is the
  cause, not a generic "both providers failed".

## Assumptions

- Index stays `halfvec(3072)` / `gemini-embedding-001`.
- Fail-closed is the chosen quota policy (not a paid second embedder).

## Out of Scope

- Supply-chain pins, MCP, ACL, changing embed dimensionality.
