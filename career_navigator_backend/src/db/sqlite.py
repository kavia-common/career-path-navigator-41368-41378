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
    """Create minimal tables needed by this backend instance.

    Important: We do NOT assume or mutate the shared 'users' table shape from the database container.
    Instead, we keep our auth persistence in a dedicated 'auth_users' table to avoid schema conflicts.
    """
    conn.executescript(
        """
        -- Dedicated auth users table for this service (text id, password_hash stored)
        CREATE TABLE IF NOT EXISTS auth_users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Jobs and progress reference auth_users.id
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES auth_users(id)
        );
        CREATE TABLE IF NOT EXISTS progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            competency TEXT NOT NULL,
            level TEXT NOT NULL,
            evidence_url TEXT,
            FOREIGN KEY(user_id) REFERENCES auth_users(id)
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


# PUBLIC_INTERFACE
def reset_users_table() -> None:
    """Drop all rows from auth_users, jobs, and progress tables for test isolation.

    Intended for use in tests when using the SQLite provider to ensure a clean state
    across test cases, especially when a shared DB path is used across runs.
    """
    with get_conn() as conn:
        _ensure_schema(conn)
        # Clear dependent tables first due to foreign keys
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM progress")
        conn.execute("DELETE FROM auth_users")
        conn.commit()


# --- Auth-specific helpers using auth_users table ---

def auth_get_user_by_email(conn: sqlite3.Connection, email_norm: str) -> Optional[dict[str, Any]]:
    """Return user record from auth_users by email."""
    return fetch_one(conn, "SELECT * FROM auth_users WHERE email = ?", (email_norm,))


def auth_get_user_by_id(conn: sqlite3.Connection, user_id: str) -> Optional[dict[str, Any]]:
    """Return user record from auth_users by id."""
    return fetch_one(conn, "SELECT * FROM auth_users WHERE id = ?", (user_id,))


def auth_insert_user(conn: sqlite3.Connection, rec: dict[str, Any]) -> None:
    """Insert a new user into auth_users."""
    execute(
        conn,
        "INSERT INTO auth_users (id, email, full_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (rec["id"], rec["email"], rec.get("full_name"), rec["password_hash"], rec["created_at"]),
    )
