"""Adjacency datasets endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from src.data_readers import json_provider

router = APIRouter(prefix="/adjacency", tags=["adjacency"])


# PUBLIC_INTERFACE
@router.get("/vs-ca", summary="Adjacency vs CA", description="Return 'Adjacency vs CA' dataset rows.")
def vs_ca():
    """Return rows for adjacency vs CA dataset."""
    return json_provider.get_ca_adjacency_vs_ca()


# PUBLIC_INTERFACE
@router.get("/matrix", summary="Adjacency matrix", description="Return 'Adjacency (Overlap %)' matrix dataset.")
def matrix():
    """Return adjacency matrix dataset."""
    return json_provider.get_adjacency_matrix()
