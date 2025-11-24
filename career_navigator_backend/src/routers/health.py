"""Health and diagnostics endpoints."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


# PUBLIC_INTERFACE
@router.get("/", summary="Health Check", description="Simple health check endpoint.", operation_id="health_check")
def health_check():
    """Return a simple health status."""
    return {"status": "ok"}
