# Feature Specification: Telegram Multi-User Roles

**Feature Branch**: `019-telegram-roles`  
**Created**: 2026-09-16  
**Status**: Verified

## User Scenarios & Testing

### User Story 1 - Several Telegram users can use the bot (Priority: P1)

As the library owner, I can allow more than one Telegram user id. Each user
has a role. Unknown ids are rejected the same way as today.

**Independent Test**: Configure two users (`admin` + `reader`). Admin can
call a mutating command. Reader can call a read command. A third id is
rejected.

### User Story 2 - Readers cannot mutate the shared library (Priority: P1)

As the library owner, a `reader` may ask and list, but must not ingest,
enrich, reindex, run arXiv `/search` that inserts `pending` rows, or rebuild
communities.

**Independent Test**: As `reader`, `/ask` and `/list` succeed; `/search`,
`/enrich`, `/reindex`, `/communities`, and ingest callbacks are rejected with
an explicit not-allowed message.

### User Story 3 - Admins keep full control (Priority: P1)

As an `admin`, I retain the full current command surface including library
mutation.

**Independent Test**: As `admin`, `/search` + ingest callback, `/enrich`,
`/reindex`, and `/communities` succeed (happy path against a known paper or
topic).

### User Story 4 - Boot fails closed without users (Priority: P2)

As the operator, a missing or empty user config must not silently open the
bot to everyone.

**Independent Test**: Start the bot with no user config (and no legacy single
id). Process exits or refuses handlers with a clear configuration error.

## Requirements

- **FR-001**: The bot MUST authorize callers by Telegram user id against a
  configured multi-user allowlist (not a single hard-coded id).
- **FR-002**: Each allowlisted user MUST have exactly one role: `admin` or
  `reader`.
- **FR-003**: Capability matrix MUST be:
  - `reader`: `/start`, `/ask`, `/list`, and non-command echo only.
  - `admin`: all current commands and ingest callbacks (`/search`, ingest
    buttons, `/enrich`, `/reindex`, `/communities`, plus reader caps).
- **FR-004**: Non-allowlisted users MUST receive the existing rejection text
  and MUST NOT run handlers.
- **FR-005**: Allowlisted users who lack the required role for a command MUST
  receive an explicit role rejection (distinct from unknown-user rejection).
- **FR-006**: Config MUST fail closed if zero users are configured.
- **FR-007**: Migration MUST accept legacy `ALLOWED_USER_ID` as a single
  `admin` when the new multi-user env is unset, so existing deploys keep
  working.
- **FR-008**: The indexed library remains one shared corpus. No
  `owner_user_id` on papers/chunks in this feature.
- **FR-009**: MCP HTTP/stdio auth MUST stay as in `018` (shared `MCP_TOKEN`).
  No per-user MCP tokens in this feature.
- **FR-010**: No new third-party auth libraries. No OAuth/OIDC. No new DB
  table required for this slice (env-based roles are enough).

## Success Criteria

- **SC-001**: Two configured users with different roles behave per FR-003.
- **SC-002**: Unknown Telegram id cannot invoke any command successfully.
- **SC-003**: `reader` cannot mutate library state (no new `pending` /
  ingest / enrich / reindex / communities rebuild).
- **SC-004**: Legacy single `ALLOWED_USER_ID` still boots as one `admin`.
- **SC-005**: Empty config fails closed.

## Assumptions

- Owner chose defaults: both surfaces long-term; identity without OAuth;
  shared library with `admin`/`reader`; first slice = Telegram roles only.
- Per-user MCP tokens are a follow-up feature (`020+`).
- OAuth IdP remains deferred.

## Out of Scope

- OAuth / OIDC / external IdP.
- Per-user MCP bearer tokens.
- Paper-level or chunk-level ACL.
- Per-user libraries / `owner_user_id`.
- Web UI, FastAPI auth, session cookies.
- Changing MCP tool surface.
