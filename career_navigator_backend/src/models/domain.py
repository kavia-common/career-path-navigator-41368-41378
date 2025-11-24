"""Domain DTOs for roles, competencies, resources, adjacency, jobs, and progress."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Role(BaseModel):
    """Canonical role entity."""
    name: str = Field(..., description="Role name")
    abbreviation: Optional[str] = Field(None, description="Short code (e.g., CA, CTO)")


class CompetencyDefinition(BaseModel):
    """Competency definition entry."""
    competency: str = Field(..., description="Competency name")
    definition: str = Field(..., description="Competency definition text")


class CompetencyMatrixRow(BaseModel):
    """Row from competencies-and-roles matrix."""
    data: Dict[str, Any] = Field(..., description="Raw row as key-value")


class Resource(BaseModel):
    """Learning or reference resource."""
    id: str = Field(..., description="Resource ID")
    title: str = Field(..., description="Resource title")
    url: Optional[str] = Field(None, description="External link")
    tags: List[str] = Field(default_factory=list, description="Tags or related competencies")


class RoleAdjacencyRow(BaseModel):
    """Adjacency entry between CA and another role."""
    role: str = Field(..., description="Role name")
    overlap_pct: float = Field(..., ge=0, le=100, description="Overlap percentage (0-100)")


class Recommendation(BaseModel):
    """Role recommendation with score and supporting resources."""
    role: str = Field(..., description="Recommended role")
    score: float = Field(..., ge=0, le=100, description="Normalized score (0-100)")
    overlap_pct: float = Field(..., ge=0, le=100, description="Adjacency overlap %")
    resources: List[Resource] = Field(default_factory=list, description="Suggested resources")


class JobApplication(BaseModel):
    """Tracked job application DTO."""
    id: str = Field(..., description="Unique ID")
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company")
    status: str = Field(..., description="Status (e.g., applied, interview, offer)")
    notes: Optional[str] = Field(None, description="Optional notes")


class ProgressItem(BaseModel):
    """User progress DTO."""
    id: str = Field(..., description="Unique ID")
    user_id: str = Field(..., description="User ID")
    competency: str = Field(..., description="Competency name")
    level: str = Field(..., description="User self-assessed level (e.g., P, A)")
    evidence_url: Optional[str] = Field(None, description="Link to evidence artifact")
