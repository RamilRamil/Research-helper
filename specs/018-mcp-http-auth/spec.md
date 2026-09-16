# Feature Specification: Public MCP Streamable HTTP

**Feature Branch**: `018-mcp-http-auth`  
**Created**: 2026-09-16  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Remote host reaches the library with a token (Priority: P1)

As the library owner, I can expose the same three read-only MCP tools over
HTTP so a remote host can use them only when it presents a shared secret.

**Independent Test**: Call the MCP HTTP endpoint without a token and with a
valid Bearer token. Without a token the call is rejected. With a token the
tools are discovered and callable.

### User Story 2 - Abuse is rate-limited (Priority: P1)

As the library owner, a noisy client cannot flood the HTTP endpoint without
hitting a server-side rate limit.

**Independent Test**: Exceed the configured request budget from one client.
Later requests receive an explicit rate-limit rejection until the window
resets.

### User Story 3 - Local stdio still works (Priority: P2)

As the library owner, the existing local stdio MCP launch remains available
and unchanged in tool surface.

**Independent Test**: Launch stdio mode and confirm the same three tools.

## Requirements

- **FR-001**: HTTP mode MUST use Streamable HTTP and expose the same three
  read-only tools as the local server: `list_papers`, `get_paper`, `search`.
- **FR-002**: HTTP mode MUST require a configured shared bearer token. Missing
  or wrong tokens MUST be rejected.
- **FR-003**: HTTP mode MUST enforce a server-side per-client request rate
  limit with an explicit rejection when exceeded.
- **FR-004**: HTTP mode MUST fail closed if the shared token is not configured.
- **FR-005**: TLS termination MAY live outside the app (reverse proxy). The app
  MUST document that cleartext HTTP is for private networks or behind TLS.
- **FR-006**: Stdio mode MUST remain available without HTTP auth.
- **FR-007**: No write tools, no `ask`, no second retrieval stack.
- **FR-008**: No new libraries beyond what is already pinned for MCP/Starlette.

## Success Criteria

- **SC-001**: Unauthorized HTTP clients cannot list or call tools.
- **SC-002**: Authorized HTTP clients can initialize, list tools, and call at
  least one tool successfully.
- **SC-003**: Exceeding the rate limit produces an explicit rejection rather
  than silent success.
- **SC-004**: Stdio mode still exposes exactly the same three tools.

## Assumptions

- Owner chose shared token auth plus rate limit (option A).
- Public exposure assumes the owner places TLS/firewall in front when needed.
- One shared token is enough while ACL remains deferred.

## Out of Scope

- Full OAuth authorization server / user login.
- Multi-tenant ACL.
- Tool `ask`.
- App-native TLS certificates.
- MCP clients that pull heterogeneous external sources.
