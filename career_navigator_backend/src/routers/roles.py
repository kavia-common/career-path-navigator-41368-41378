"""Roles endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from src.data_readers import json_provider
from src.models.domain import Role

router = APIRouter(prefix="/roles", tags=["roles"])


# PUBLIC_INTERFACE
@router.get("/", response_model=List[Role], summary="List roles", description="List canonical roles with abbreviations.")
def list_roles():
    """List roles from role abbreviations dataset."""
    data = json_provider.get_role_abbreviations()
    rows = data.get("rows", [])
    out: list[Role] = []
    for r in rows:
        role = r.get("Role")
        abbr = r.get("Abbreviation")
        if not role:
            continue
        out.append(Role(name=str(role), abbreviation=str(abbr) if abbr else None))
    return out
