"""Auth and user-facing DTOs."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="Full name for display")


class UserCreate(UserBase):
    """Registration payload."""
    password: str = Field(..., min_length=8, description="Raw password (not stored).")


class UserLogin(BaseModel):
    """Login payload."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password")


class UserPublic(UserBase):
    """Safe user representation."""
    id: str = Field(..., description="User identifier")


class TokenResponse(BaseModel):
    """Access token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type (bearer)")


class MeResponse(UserPublic):
    """Response for /auth/me."""
    pass
