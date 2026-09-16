# Feature Specification: Exact Dependency Pins

**Feature Branch**: `016-supply-chain-pins`  
**Created**: 2026-09-16  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Rebuilds install the same packages (Priority: P1)

As bot owner, rebuilding the app image installs the same dependency
versions that were verified on the live container, not whatever latest
matches a loose range.

**Why this priority**: constitution VI; silent dependency drift breaks
RAG and bot quietly.

**Independent Test**: `requirements.txt` uses exact versions. A clean
image build succeeds with those pins.

**Acceptance Scenarios**:

1. **Given** the live container freeze, **when** `requirements.txt` is
   updated, **then** every direct and transitive package needed to run
   the bot is pinned with `==`.
2. **Given** the pinned file, **when** the app image is rebuilt,
   **then** `pip install` succeeds without resolving newer majors.

---

## Requirements

- **FR-001**: `requirements.txt` MUST pin packages with exact versions
  (`==`), taken from a freeze of the working app image.
- **FR-002**: MUST NOT add hash pinning or GitHub Actions in this slice.
- **FR-003**: No new libraries beyond what the freeze already installs.
- **FR-004**: Bot image MUST rebuild successfully after the pin file
  replaces loose ranges.

## Success Criteria

- **SC-001**: Zero unpinned `>=` / bare ranges remain in the install
  requirements used by Docker.
- **SC-002**: One clean `docker compose build` of `app` completes.

## Assumptions

- Owner chose pin-only (A), not hashes (B) or CI (C).
- Freeze source is the current working `app` image.

## Out of Scope

- `--require-hashes`, Dependabot, GitHub Actions, MCP, ACL.
