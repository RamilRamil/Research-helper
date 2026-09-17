"""Durable MCP topic ingest jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

import psycopg
from dotenv import load_dotenv

load_dotenv()

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
_TOPIC_MAX = 200


@dataclass(frozen=True)
class TopicIngestJob:
    id: int
    topic: str
    status: str
    creator_credential_id: int | None
    created_at: datetime | None
    updated_at: datetime | None
    finished_at: datetime | None
    error: str | None
    found_count: int
    indexed_count: int
    failed_count: int


def _row_to_job(row: tuple) -> TopicIngestJob:
    return TopicIngestJob(
        id=int(row[0]),
        topic=str(row[1]),
        status=str(row[2]),
        creator_credential_id=int(row[3]) if row[3] is not None else None,
        created_at=row[4],
        updated_at=row[5],
        finished_at=row[6],
        error=str(row[7]) if row[7] is not None else None,
        found_count=int(row[8] or 0),
        indexed_count=int(row[9] or 0),
        failed_count=int(row[10] or 0),
    )


_SELECT = """
    id, topic, status, creator_credential_id,
    created_at, updated_at, finished_at, error,
    found_count, indexed_count, failed_count
"""


def normalize_topic(topic: str) -> str:
    clean = (topic or "").strip()
    if not clean:
        raise ValueError("topic must be non-empty")
    if len(clean) > _TOPIC_MAX:
        raise ValueError(f"topic must be at most {_TOPIC_MAX} characters")
    return clean


def enqueue(topic: str, creator_credential_id: int) -> TopicIngestJob:
    clean = normalize_topic(topic)
    if creator_credential_id < 1:
        raise ValueError("creator_credential_id must be positive")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            f"""
            INSERT INTO mcp_topic_jobs (topic, status, creator_credential_id)
            VALUES (%s, %s, %s)
            RETURNING {_SELECT}
            """,
            (clean, STATUS_QUEUED, creator_credential_id),
        ).fetchone()
        conn.commit()
    assert row is not None
    return _row_to_job(row)


def get_job(job_id: int) -> TopicIngestJob | None:
    if job_id < 1:
        return None
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            f"SELECT {_SELECT} FROM mcp_topic_jobs WHERE id = %s",
            (job_id,),
        ).fetchone()
    return _row_to_job(row) if row else None


def claim_next_queued() -> TopicIngestJob | None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            f"""
            WITH next AS (
                SELECT id
                FROM mcp_topic_jobs
                WHERE status = %s
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE mcp_topic_jobs j
            SET status = %s,
                updated_at = now()
            FROM next
            WHERE j.id = next.id
            RETURNING j.id, j.topic, j.status, j.creator_credential_id,
                      j.created_at, j.updated_at, j.finished_at, j.error,
                      j.found_count, j.indexed_count, j.failed_count
            """,
            (STATUS_QUEUED, STATUS_RUNNING),
        ).fetchone()
        conn.commit()
    return _row_to_job(row) if row else None


def mark_succeeded(
    job_id: int,
    *,
    found_count: int,
    indexed_count: int,
    failed_count: int,
) -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE mcp_topic_jobs
            SET status = %s,
                found_count = %s,
                indexed_count = %s,
                failed_count = %s,
                error = NULL,
                updated_at = now(),
                finished_at = now()
            WHERE id = %s
            """,
            (
                STATUS_SUCCEEDED,
                found_count,
                indexed_count,
                failed_count,
                job_id,
            ),
        )
        conn.commit()


def mark_failed(job_id: int, error: str) -> None:
    safe = (error or "unknown error").replace("\x00", "")[:500]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(
            """
            UPDATE mcp_topic_jobs
            SET status = %s,
                error = %s,
                updated_at = now(),
                finished_at = now()
            WHERE id = %s
            """,
            (STATUS_FAILED, safe, job_id),
        )
        conn.commit()


def job_to_public_dict(job: TopicIngestJob) -> dict:
    def _ts(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    return {
        "job_id": job.id,
        "topic": job.topic,
        "status": job.status,
        "created_at": _ts(job.created_at),
        "updated_at": _ts(job.updated_at),
        "finished_at": _ts(job.finished_at),
        "error": job.error,
        "found_count": job.found_count,
        "indexed_count": job.indexed_count,
        "failed_count": job.failed_count,
    }
