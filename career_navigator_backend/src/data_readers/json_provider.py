"""JSON data provider for static datasets in data/ directory.

Caches files in-memory to minimize I/O. Validates basic shapes where useful.

PySecure-4-Minimal:
- Validate input filename to prevent path traversal.
- Handle errors with structured exceptions (no stack leaks).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

from src.core.config import get_settings


DATA_EXT = ".json"


def _data_dir() -> Path:
    settings = get_settings()
    return Path(settings.data_dir).resolve()


def _validate_filename(name: str) -> str:
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid dataset name")
    if not name.endswith(DATA_EXT):
        raise HTTPException(status_code=400, detail="Dataset must be a .json file")
    return name


@lru_cache(maxsize=256)
def load_dataset(name: str) -> Dict[str, Any]:
    """Load a JSON dataset by filename from the configured data directory."""
    fname = _validate_filename(name)
    path = _data_dir() / fname
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {fname}")
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Dataset parse error: {fname}")


def list_datasets() -> List[str]:
    """List available dataset JSON files."""
    d = _data_dir()
    if not d.exists():
        return []
    return sorted([p.name for p in d.glob(f"*{DATA_EXT}") if p.is_file()])


def get_ca_adjacency_vs_ca() -> Dict[str, Any]:
    """Convenience accessor for 'Adjacency vs CA' primary dataset."""
    # Prefer the 20251124_105429 (main) file
    candidates = [
        "20251124_105429_CA_Role_Adjacency__Adjacency vs CA.json",
        "20251124_105431_CA_Role_Adjacency29__Adjacency (Overlap %).json",
    ]
    for c in candidates:
        try:
            return load_dataset(c)
        except HTTPException:
            continue
    raise HTTPException(status_code=404, detail="Adjacency dataset not found")


def get_adjacency_matrix() -> Dict[str, Any]:
    """Return the adjacency matrix (Overlap %) dataset."""
    candidates = [
        "20251124_105429_CA_Role_Adjacency__Adjacency (Overlap %).json",
        "20251124_105431_CA_Role_Adjacency29__Adjacency (Overlap %).json",
    ]
    for c in candidates:
        try:
            return load_dataset(c)
        except HTTPException:
            continue
    raise HTTPException(status_code=404, detail="Adjacency matrix not found")


def get_competencies_and_roles() -> Dict[str, Any]:
    return load_dataset("20251124_105432_Competency_mapping__Competencies and roles.json")


def get_competency_definitions() -> Dict[str, Any]:
    return load_dataset("20251124_105432_Competency_mapping__Competency Definitions.json")


def get_role_abbreviations() -> Dict[str, Any]:
    return load_dataset("20251124_105432_Competency_mapping__Role abbreviations.json")


def get_navigator_sheet() -> Dict[str, Any]:
    return load_dataset("20251124_105432_Role_Navigator_Worksheet__Navigator.json")
