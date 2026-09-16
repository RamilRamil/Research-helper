"""Telegram allowlist with admin/reader roles (env-based)."""

from __future__ import annotations

import os
from collections.abc import Mapping

ROLE_ADMIN = "admin"
ROLE_READER = "reader"
_ROLES = frozenset({ROLE_ADMIN, ROLE_READER})

MSG_UNKNOWN_USER = "You are not allowed to use this bot"
MSG_WRONG_ROLE = "You are not allowed to use this command"

_USERS: dict[int, str] | None = None


def _parse_allowed_users(raw: str) -> dict[int, str]:
    users: dict[int, str] = {}
    for part in raw.split(","):
        entry = part.strip()
        if not entry:
            raise ValueError("Empty entry in ALLOWED_USERS")
        if ":" not in entry:
            raise ValueError(f"Invalid ALLOWED_USERS entry: {entry!r}")
        id_s, role_s = entry.split(":", 1)
        id_s, role_s = id_s.strip(), role_s.strip()
        try:
            uid = int(id_s)
        except ValueError as e:
            raise ValueError(f"Invalid telegram id in ALLOWED_USERS: {id_s!r}") from e
        if role_s not in _ROLES:
            raise ValueError(f"Invalid role in ALLOWED_USERS: {role_s!r}")
        if uid in users:
            raise ValueError(f"Duplicate telegram id in ALLOWED_USERS: {uid}")
        users[uid] = role_s
    if not users:
        raise ValueError("ALLOWED_USERS is empty")
    return users


def load_users(environ: Mapping[str, str] | None = None) -> dict[int, str]:
    """Parse ALLOWED_USERS or legacy ALLOWED_USER_ID. Fail closed if empty/invalid.

    When ``environ`` is omitted, also caches the result for ``role_of`` / ``require``.
    """
    global _USERS
    env = os.environ if environ is None else environ
    raw = (env.get("ALLOWED_USERS") or "").strip()
    if raw:
        users = _parse_allowed_users(raw)
    else:
        legacy = (env.get("ALLOWED_USER_ID") or "").strip()
        if not legacy:
            raise ValueError(
                "No Telegram users configured: set ALLOWED_USERS or ALLOWED_USER_ID"
            )
        try:
            uid = int(legacy)
        except ValueError as e:
            raise ValueError("ALLOWED_USER_ID must be an integer") from e
        users = {uid: ROLE_ADMIN}
    if environ is None:
        _USERS = users
    return users


def role_of(user_id: int) -> str | None:
    users = _USERS if _USERS is not None else load_users()
    return users.get(user_id)


def require(user_id: int, *roles: str) -> bool:
    role = role_of(user_id)
    return role is not None and role in roles


def denied_message(user_id: int | None, *roles: str) -> str | None:
    """Return rejection text, or None if access is allowed."""
    if user_id is None or role_of(user_id) is None:
        return MSG_UNKNOWN_USER
    if not require(user_id, *roles):
        return MSG_WRONG_ROLE
    return None
