"""Datasets listing and retrieval."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path

from src.data_readers import json_provider

router = APIRouter(prefix="/datasets", tags=["datasets"])


# PUBLIC_INTERFACE
@router.get("/", summary="List datasets", description="List available JSON datasets from the data directory.")
def list_available():
    """List dataset filenames."""
    return {"datasets": json_provider.list_datasets()}


# PUBLIC_INTERFACE
@router.get("/{name}", summary="Get dataset by name", description="Retrieve a JSON dataset by filename (must end with .json).")
def get_dataset(name: str = Path(..., description="Dataset filename (e.g., file.json)")):
    """Return a raw dataset JSON object."""
    if not name.endswith(".json"):
        raise HTTPException(status_code=400, detail="Dataset must be a .json file")
    return json_provider.load_dataset(name)
