"""Recommendation service using adjacency overlap datasets.

Computes simple deterministic scores based on 'Adjacency vs CA' overlap percentages.
Filters by a minimum threshold, normalizes to 0-100, and augments results
with related resources (placeholder mapping based on role/competency tags).

PySecure-4-Minimal:
- Validate numeric inputs.
- No sensitive logs.
"""
from __future__ import annotations

from typing import List

from src.data_readers import json_provider
from src.models.domain import Recommendation, Resource


def _resource_suggestions_for_role(role: str) -> list[Resource]:
    # Simple deterministic mapping for MVP; could be enhanced later
    base = role.lower()
    items: list[Resource] = []
    if "technology officer" in base or "cto" in base:
        items.append(Resource(id="res-cto-1", title="Developer Experience & Golden Paths", url=None, tags=["IDP & DevEx"]))
        items.append(Resource(id="res-cto-2", title="Portfolio & FinOps Basics", url=None, tags=["FinOps & Capacity"]))
    if "information officer" in base and "business unit" in base:
        items.append(Resource(id="res-bucio-1", title="Service Catalog & XLAs", url=None, tags=["Service Catalog & XLAs"]))
    if "strategy" in base:
        items.append(Resource(id="res-cso-1", title="Strategy → Capability Mapping", url=None, tags=["Strategy-to-Capability"]))
    if not items:
        items.append(Resource(id="res-generic-1", title="Executive Storytelling", url=None, tags=["External Signaling"]))
    return items


# PUBLIC_INTERFACE
def recommend_for_ca(min_overlap: float = 55.0, limit: int = 10) -> List[Recommendation]:
    """Return recommended roles for Chief Architect based on overlap thresholds.

    Args:
        min_overlap: Minimum Overlap with Chief Architect (%) to include.
        limit: Max number of recommendations.

    Returns:
        List of Recommendation DTOs sorted by overlap descending.
    """
    if min_overlap < 0 or min_overlap > 100:
        min_overlap = 55.0
    if limit <= 0 or limit > 50:
        limit = 10

    data = json_provider.get_ca_adjacency_vs_ca()
    rows = data.get("rows", [])
    recs: list[Recommendation] = []
    for r in rows:
        role = r.get("Role")
        overlap = r.get("Overlap with Chief Architect (%)")
        if role is None or overlap is None:
            continue
        try:
            overlap_f = float(overlap)
        except (ValueError, TypeError):
            continue
        if role == "Chief Architect":
            continue
        if overlap_f < min_overlap:
            continue
        score = overlap_f  # direct mapping for MVP
        recs.append(
            Recommendation(
                role=role,
                score=round(score, 2),
                overlap_pct=round(overlap_f, 2),
                resources=_resource_suggestions_for_role(role),
            )
        )
    # Sort by score desc and truncate
    recs.sort(key=lambda x: x.score, reverse=True)
    return recs[:limit]
