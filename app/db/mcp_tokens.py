"""MCP credential directory: create, revoke, verify by hash."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()

ROLE_ADMIN = "admin"
ROLE_READER = "reader"
_ROLES = frozenset({ROLE_ADMIN, ROLE_READER})
LAST_USED_COALESCE = timedelta(seconds=60)


@dataclass(frozen=True)
class McpCredential:
    id: int
    label: str
    role: str


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def create_token(label: str, role: str) -> tuple[McpCredential, str]:
    clean_label = (label or "").strip()
    clean_role = (role or "").strip()
    if not clean_label:
        raise ValueError("label must be non-empty")
    if clean_role not in _ROLES:
        raise ValueError("role must be admin or reader")
    raw = generate_secret()
    digest = hash_token(raw)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO mcp_tokens (label, role, token_hash)
                VALUES (%s, %s, %s)
                RETURNING id, label, role
                """,
                (clean_label, clean_role, digest),
            ).fetchone()
        except psycopg.Error as e:
            msg = str(e)
            if "mcp_tokens_active_label_uidx" in msg or "unique" in msg.lower():
                raise ValueError(
                    f"active credential already exists for label: {clean_label}"
                ) from e
            raise
        conn.commit()
    assert row is not None
    return McpCredential(id=int(row[0]), label=str(row[1]), role=str(row[2])), raw


def revoke_token(label: str) -> McpCredential:
    clean_label = (label or "").strip()
    if not clean_label:
        raise ValueError("label must be non-empty")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            """
            UPDATE mcp_tokens
            SET revoked_at = now()
            WHERE label = %s AND revoked_at IS NULL
            RETURNING id, label, role
            """,
            (clean_label,),
        ).fetchone()
        conn.commit()
    if row is None:
        raise ValueError(f"no active credential for label: {clean_label}")
    return McpCredential(id=int(row[0]), label=str(row[1]), role=str(row[2]))


def lookup_active_by_raw(raw: str) -> McpCredential | None:
    if not raw:
        return None
    digest = hash_token(raw)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            """
            SELECT id, label, role, token_hash
            FROM mcp_tokens
            WHERE revoked_at IS NULL AND token_hash = %s
            """,
            (digest,),
        ).fetchone()
    if row is None:
        return None
    stored = str(row[3])
    if not hmac.compare_digest(stored, digest):
        return None
    return McpCredential(id=int(row[0]), label=str(row[1]), role=str(row[2]))


def touch_last_used(credential_id: int) -> None:
    cutoff = datetime.now(timezone.utc) - LAST_USED_COALESCE
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE mcp_tokens
            SET last_used_at = now()
            WHERE id = %s
              AND revoked_at IS NULL
              AND (last_used_at IS NULL OR last_used_at < %s)
            """,
            (credential_id, cutoff),
        )
        conn.commit()


def count_active() -> int:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            "SELECT count(*) FROM mcp_tokens WHERE revoked_at IS NULL"
        ).fetchone()
    return int(row[0]) if row else 0
