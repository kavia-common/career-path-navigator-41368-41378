"""Jobs tracking endpoints."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.routers.auth import get_current_user
from src.models.auth import UserPublic
from src.models.domain import JobApplication
from src.core.config import get_settings
from src.db import sqlite as sqlite_db

router = APIRouter(prefix="/jobs", tags=["jobs"])

# In-memory fallback store
_mem_jobs: Dict[str, Dict] = {}  # id -> record
_user_jobs_index: Dict[str, List[str]] = {}  # user_id -> list[job_id]


class JobCreate(BaseModel):
    title: str = Field(..., min_length=2)
    company: str = Field(..., min_length=1)
    status: str = Field(..., min_length=2)
    notes: Optional[str] = Field(None)


def _add_job(rec: Dict) -> None:
    settings = get_settings()
    if settings.data_provider == "sqlite":
        with sqlite_db.get_conn() as conn:
            sqlite_db.execute(
                conn,
                "INSERT INTO jobs (id, user_id, title, company, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (rec["id"], rec["user_id"], rec["title"], rec["company"], rec["status"], rec.get("notes")),
            )
    else:
        _mem_jobs[rec["id"]] = rec
        _user_jobs_index.setdefault(rec["user_id"], []).append(rec["id"])


def _list_jobs(user_id: str) -> List[Dict]:
    settings = get_settings()
    if settings.data_provider == "sqlite":
        with sqlite_db.get_conn() as conn:
            return sqlite_db.fetch_all(conn, "SELECT * FROM jobs WHERE user_id = ?", (user_id,))
    ids = _user_jobs_index.get(user_id, [])
    return [ _mem_jobs[i] for i in ids if i in _mem_jobs ]


# PUBLIC_INTERFACE
@router.get("/", response_model=List[JobApplication], summary="List my jobs", description="List job applications for current user.")
def list_my_jobs(current: UserPublic = Depends(get_current_user)):
    """List job applications for current user."""
    rows = _list_jobs(current.id)
    return [JobApplication(**r) for r in rows]


# PUBLIC_INTERFACE
@router.post("/", response_model=JobApplication, status_code=status.HTTP_201_CREATED, summary="Add job", description="Add a job application for current user.")
def add_job(payload: JobCreate, current: UserPublic = Depends(get_current_user)):
    """Add a job application."""
    rec = {
        "id": str(uuid4()),
        "user_id": current.id,
        "title": payload.title.strip(),
        "company": payload.company.strip(),
        "status": payload.status.strip(),
        "notes": payload.notes.strip() if payload.notes else None,
    }
    _add_job(rec)
    return JobApplication(**rec)
