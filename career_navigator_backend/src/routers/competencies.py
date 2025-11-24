"""Competencies endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from src.data_readers import json_provider
from src.models.domain import CompetencyDefinition

router = APIRouter(prefix="/competencies", tags=["competencies"])


# PUBLIC_INTERFACE
@router.get("/definitions", response_model=List[CompetencyDefinition], summary="Competency definitions", description="Return competency definitions for glossary.")
def definitions():
    """Return competency definitions."""
    data = json_provider.get_competency_definitions()
    rows = data.get("rows", [])
    out: list[CompetencyDefinition] = []
    for r in rows:
        c = r.get("Competency")
        d = r.get("Definition")
        if not c or not d:
            continue
        out.append(CompetencyDefinition(competency=str(c), definition=str(d)))
    return out


# PUBLIC_INTERFACE
@router.get("/matrix", summary="Competency matrix", description="Return raw 'Competencies and roles' matrix.")
def matrix():
    """Return the raw matrix for UI rendering."""
    return json_provider.get_competencies_and_roles()
