"""SQLite database helper and simple repositories for users, jobs, and progress.

Only used when DATA_PROVIDER=sqlite. Otherwise, simple in-memory stores are used.

PySecure-4-Minimal:
- Use parameterized queries.
- Ensure connections are closed via context managers.
- Avoid logging sensitive data.
- Create DB directory if missing; initialize schema on first connect.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional

from src.core.config import get_settings


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            competency TEXT NOT NULL,
            level TEXT NOT NULL,
            evidence_url TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()


@contextmanager
def get_conn():
    settings = get_settings()
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Use check_same_thread=False to prevent thread-affinity errors under TestClient or background tasks.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    try:
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def fetch_all(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, list(params))
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def fetch_one(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> Optional[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(query, list(params))
    row = cur.fetchone()
    return dict(row) if row else None


def execute(conn: sqlite3.Connection, query: str, params: Iterable[Any]) -> None:
    conn.execute(query, list(params))
    conn.commit()
