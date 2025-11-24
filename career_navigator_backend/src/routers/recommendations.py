"""Recommendations endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query

from src.services.recommendations import recommend_for_ca
from src.models.domain import Recommendation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# PUBLIC_INTERFACE
@router.get("/for-ca", response_model=List[Recommendation], summary="Recommend roles for CA", description="Return role recommendations based on adjacency overlap with Chief Architect.")
def for_ca(min_overlap: float = Query(55.0, ge=0, le=100, description="Minimum overlap % to include"),
           limit: int = Query(10, ge=1, le=50, description="Maximum number of results")):
    """Return deterministic recommendations based on overlap thresholds."""
    return recommend_for_ca(min_overlap=min_overlap, limit=limit)
