"""Resources endpoints (MVP static)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from src.models.domain import Resource

router = APIRouter(prefix="/resources", tags=["resources"])


# PUBLIC_INTERFACE
@router.get("/", response_model=List[Resource], summary="List resources", description="Return a small static set of resources for MVP.")
def list_resources():
    """Return static resources."""
    return [
        Resource(id="res-cto-1", title="Developer Experience & Golden Paths", url=None, tags=["IDP & DevEx"]),
        Resource(id="res-cto-2", title="Portfolio & FinOps Basics", url=None, tags=["FinOps & Capacity"]),
        Resource(id="res-generic-1", title="Executive Storytelling", url=None, tags=["External Signaling"]),
    ]
