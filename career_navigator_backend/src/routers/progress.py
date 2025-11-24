"""User progress endpoints."""
from __future__ import annotations

from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field

from src.routers.auth import get_current_user
from src.models.auth import UserPublic
from src.models.domain import ProgressItem
from src.core.config import get_settings
from src.db import sqlite as sqlite_db

router = APIRouter(prefix="/progress", tags=["progress"])

# In-memory fallback
_mem_progress: Dict[str, Dict] = {}
_user_progress_index: Dict[str, List[str]] = {}


class ProgressCreate(BaseModel):
    competency: str = Field(..., min_length=2)
    level: str = Field(..., min_length=1)
    evidence_url: Optional[str] = Field(None)


def _add_progress(rec: Dict) -> None:
    settings = get_settings()
    if settings.data_provider == "sqlite":
        try:
            with sqlite_db.get_conn() as conn:
                sqlite_db.execute(
                    conn,
                    "INSERT INTO progress (id, user_id, competency, level, evidence_url) VALUES (?, ?, ?, ?, ?)",
                    (rec["id"], rec["user_id"], rec["competency"], rec["level"], rec.get("evidence_url")),
                )
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to persist progress")
    else:
        _mem_progress[rec["id"]] = rec
        _user_progress_index.setdefault(rec["user_id"], []).append(rec["id"])


def _list_progress(user_id: str) -> List[Dict]:
    settings = get_settings()
    if settings.data_provider == "sqlite":
        try:
            with sqlite_db.get_conn() as conn:
                return sqlite_db.fetch_all(conn, "SELECT * FROM progress WHERE user_id = ?", (user_id,))
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to load progress")
    ids = _user_progress_index.get(user_id, [])
    return [_mem_progress[i] for i in ids if i in _mem_progress]


# PUBLIC_INTERFACE
@router.get("/", response_model=List[ProgressItem], summary="List my progress", description="List progress items for current user.")
def list_my_progress(current: UserPublic = Depends(get_current_user)):
    """List progress for current user."""
    rows = _list_progress(current.id)
    return [ProgressItem(**r) for r in rows]


# PUBLIC_INTERFACE
@router.post("/", response_model=ProgressItem, status_code=status.HTTP_201_CREATED, summary="Add progress", description="Add a progress item for current user.")
def add_progress(payload: ProgressCreate, current: UserPublic = Depends(get_current_user)):
    """Add a progress item."""
    rec = {
        "id": str(uuid4()),
        "user_id": current.id,
        "competency": payload.competency.strip(),
        "level": payload.level.strip(),
        "evidence_url": payload.evidence_url.strip() if payload.evidence_url else None,
    }
    _add_progress(rec)
    return ProgressItem(**rec)
