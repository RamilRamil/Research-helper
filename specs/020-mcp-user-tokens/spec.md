# Feature Specification: MCP Per-User Tokens

**Feature Branch**: `020-mcp-user-tokens`  
**Created**: 2026-09-17  
**Status**: Verified

## Clarifications

### Session 2026-09-17

- Q: Cutover from former shared env secret → A: Mint fresh only; never
  import the old shared secret into the credential directory.
- Q: Label uniqueness → A: Unique among active credentials only; reuse
  after revoke allowed.
- Q: Credential lifetime → A: No expiry; active until explicit revoke only.
- Q: Who sets the secret at mint → A: System generates; show once to
  operator.
- Q: last_used on successful HTTP auth → A: Update at most once per short
  time window (not on every request).

## User Scenarios & Testing

### User Story 1 - Each remote client has its own credential (Priority: P1)

As the library owner, I can issue a distinct MCP credential for each remote
client. That credential is tied to a stable identity (label) and a role.
A client presenting its credential can use the existing read-only MCP tools
over HTTP against the shared library.

**Independent Test**: Create two active credentials (different labels). Each
Bearer succeeds at tool discovery and at least one tool call. A third
unknown Bearer is rejected. Creating a second active credential with an
already-active label is rejected.

### User Story 2 - Revoke one client without touching others (Priority: P1)

As the library owner, I can revoke a single client's credential so that
client loses HTTP access immediately while other clients keep working.

**Independent Test**: Revoke credential A. A's next HTTP call fails. B's call
still succeeds.

### User Story 3 - Shared env token is gone (Priority: P1)

As the operator, HTTP no longer accepts a single shared environment secret.
Only credentials stored in the user/token directory count. Cutover is mint
fresh credentials and point clients at them; the old shared secret is never
imported into the directory.

**Independent Test**: With an active directory credential configured, setting
or unsetting the former shared env secret does not grant HTTP access by
itself. Only a valid directory credential works. An operator procedure that
only sets the old env secret (no directory rows) still fails closed.

### User Story 4 - Abuse limits by network and by identity (Priority: P1)

As the library owner, noisy traffic is limited both before a client is
identified (by client network address) and after (by credential identity),
so one client behind NAT cannot starve others only by sharing an IP, and
anonymous flood is still bounded.

**Independent Test**: Exceed the per-address budget without a valid
credential and observe rejection. Separately, exceed the per-credential
budget with a valid credential and observe rejection while another
credential on the same address can still proceed within its own budget.

### User Story 5 - Local stdio stays simple (Priority: P2)

As a local operator, launching MCP over stdio on the host still works
without presenting a per-user credential (host trust).

**Independent Test**: Stdio mode exposes the same three read-only tools
without a Bearer token.

### User Story 6 - Empty directory fails closed for HTTP (Priority: P2)

As the operator, HTTP mode must not serve the library if there are zero
active credentials.

**Independent Test**: Start or call HTTP with an empty active credential
set. Requests are rejected with a clear auth failure; the library is not
readable anonymously.

## Requirements

- **FR-001**: HTTP MCP MUST authorize callers only via credentials stored in
  a durable operator-managed directory (not a single shared env secret).
- **FR-002**: Each credential MUST have a stable label, exactly one role
  (`admin` or `reader`), and an active/revoked state. Among active
  credentials, labels MUST be unique; after revoke, the same label MAY be
  issued again on a new credential. Credentials MUST NOT expire by time in
  this feature; only revoke ends access.
- **FR-003**: At-rest credential secrets MUST NOT be stored in recoverable
  plaintext; verification MUST use a one-way form of the secret.
- **FR-004**: Any active credential (either role) MUST be allowed to use the
  existing three read-only tools (`list_papers`, `get_paper`, `search`) on
  the shared library. Roles MUST be recorded for identity, limits, and
  future ACL; this feature MUST NOT filter papers by owner.
- **FR-005**: Missing, unknown, or revoked credentials MUST be rejected for
  HTTP tool discovery and tool calls.
- **FR-006**: The former shared HTTP env token MUST NOT grant access and MUST
  NOT be auto-imported into the credential directory.
- **FR-007**: HTTP MUST enforce request rate limits keyed by client network
  address when the caller is not yet accepted as an identity, and keyed by
  credential identity after successful verification.
- **FR-008**: HTTP MUST fail closed when zero active credentials exist.
- **FR-009**: Stdio MCP MUST remain available without per-user credentials
  and MUST keep the same three-tool surface.
- **FR-010**: Operators MUST be able to create and revoke credentials without
  a web UI (documented operator procedure is enough). Create MUST generate
  the secret in the system and present it once; the operator MUST NOT be
  required to invent the secret.
- **FR-011**: No OAuth/OIDC. No paper/chunk ACL. No new MCP write/`ask`
  tools. No merge of Telegram identities with MCP credentials in this
  feature.
- **FR-012**: No new third-party auth libraries beyond what is already pinned
  for MCP/HTTP.
- **FR-013**: On successful HTTP credential verification the system MUST
  record last-used time for that credential, but MUST NOT require a write
  on every request; updates MAY be coalesced to at most once per short
  time window.

## Success Criteria

- **SC-001**: Two distinct active credentials can independently use HTTP MCP
  tools; an unknown credential cannot.
- **SC-002**: Revoking one credential blocks only that client.
- **SC-003**: The former shared env token alone cannot authorize HTTP access.
- **SC-004**: Rate-limit rejection occurs both for over-budget anonymous /
  unverified traffic by address and for over-budget traffic by credential.
- **SC-005**: Stdio mode still exposes exactly the three read-only tools
  without a per-user credential.
- **SC-006**: With zero active credentials, HTTP does not expose library
  data.
- **SC-007**: After successful HTTP use, a credential's last-used marker
  advances within a short window without requiring a durable write on every
  single request.

## Key Entities

- **MCP credential**: label (unique among active), role (`admin` | `reader`),
  secret verifier, active/revoked, created/revoked timestamps, last-used
  marker updated on successful HTTP auth at most once per short window. No
  time-based expiry in this feature. Revoked rows MAY keep their label for
  history while a new active credential reuses that label.
- **Shared library**: unchanged single indexed corpus; no per-credential
  paper ownership in this feature.

## Assumptions

- Owner decisions for this slice: durable directory in the existing database;
  hard removal of shared env token; identity + role without paper ACL;
  stdio remains host-trusted; dual rate-limit keys (address + identity).
- Issuing a credential: the system generates the secret and shows it once to
  the operator; afterward only the verifier is kept. Cutover never copies
  the former shared env secret into the directory; operators mint new
  credentials before relying on HTTP. Rotation is revoke then mint (same
  label allowed after revoke).
- Telegram `ALLOWED_USERS` stays a separate surface until a later identity
  merge feature.
- TLS remains outside the app (reverse proxy), same as `018`.
- Exact last_used coalesce window and rate-limit numeric budgets are plan
  defaults unless ops needs differ.

## Out of Scope

- OAuth / OIDC / external IdP.
- Paper-level or chunk-level ACL.
- Per-user libraries / `owner_user_id` on papers.
- Merging Telegram users with MCP credentials.
- Admin UI for token management.
- Operator-chosen credential secrets at mint (system generate only).
- Time-based credential expiry / TTL.
- MCP write tools or `/ask` over MCP.
- Changing stdio to require Bearer auth.
