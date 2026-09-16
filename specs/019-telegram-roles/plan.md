# Plan: Telegram Multi-User Roles

## Approach

Keep auth env-based. No new tables or libraries.

### Config

Prefer:

```text
ALLOWED_USERS=111:admin,222:reader
```

Rules:
- `telegram_id:role`, comma-separated
- roles: `admin` | `reader` only
- duplicate ids -> fail closed at boot
- bad role / bad int -> fail closed at boot

Legacy:
- If `ALLOWED_USERS` unset/empty and `ALLOWED_USER_ID` set -> one `admin`
- If both empty -> fail closed

### Code

- New small module `app/bot/auth.py` (or equivalent next to bot):
  - `load_users() -> dict[int, str]`
  - `role_of(user_id) -> str | None`
  - `require(user_id, *roles) -> bool`
- `app/bot/main.py`: replace `is_allowed` / single `ALLOWED` with role checks
  per handler capability map from FR-003.
- Rejection strings:
  - unknown user: keep `You are not allowed to use this bot`
  - wrong role: `You are not allowed to use this command` (ASCII)

### Docs / env

- `.env.example`: document `ALLOWED_USERS`; keep `ALLOWED_USER_ID` as legacy
- `docs/configuration.md` + `.ru.md`, `docs/bot-commands.md` + `.ru.md`
- `RAG_UPGRADE_PLAN.md` / `specs/README.md`: mark `019` active

### Verify

Without running a full Telegram session if awkward, use a unit-style check
inside the container:

1. Parse matrix: admin/reader/unknown
2. Boot path: legacy `ALLOWED_USER_ID` alone loads one admin
3. Boot path: empty config raises

Handler wiring: code review that every mutating handler calls `admin`.

## Non-goals

MCP token changes, OAuth, DB users table.
