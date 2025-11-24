"""Authentication routes: register, login, me.

Uses SQLite when DATA_PROVIDER=sqlite; otherwise uses in-memory store.

PySecure-4-Minimal:
- Validate inputs via Pydantic models.
- Hash passwords; do not log secrets.
- Use Bearer token with JWT.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import EmailStr

from src.core.config import get_settings
from src.security.jwt import create_access_token, decode_token, hash_password, verify_password
from src.models.auth import UserCreate, UserLogin, TokenResponse, UserPublic, MeResponse
from src.db import sqlite as sqlite_db
import sqlite3

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# In-memory fallback stores (for MVP when using JSON provider)
_mem_users: Dict[str, Dict] = {}  # id -> record
_mem_users_by_email: Dict[str, str] = {}  # email -> id

# PUBLIC_INTERFACE
def reset_auth_state() -> None:
    """Reset in-memory auth state for tests or local dev.

    Note:
        - This only clears in-memory user stores when DATA_PROVIDER != "sqlite".
        - When using SQLite provider, users are persisted in the DB and are not cleared.
    """
    settings = get_settings()
    if settings.data_provider != "sqlite":
        _mem_users.clear()
        _mem_users_by_email.clear()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _get_user_by_email(email: str) -> Optional[Dict]:
    settings = get_settings()
    email_norm = _normalize_email(email)
    if settings.data_provider == "sqlite":
        try:
            with sqlite_db.get_conn() as conn:
                row = sqlite_db.fetch_one(conn, "SELECT * FROM users WHERE email = ?", (email_norm,))
                return row
        except sqlite3.OperationalError:
            # Map to client error
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database operation failed")
        except sqlite3.DatabaseError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database operation failed")
    # In-memory
    uid = _mem_users_by_email.get(email_norm)
    return _mem_users.get(uid) if uid else None


def _create_user(email: EmailStr, full_name: Optional[str], pwd_hash: str) -> Dict:
    settings = get_settings()
    uid = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    full_name_norm = full_name.strip() if isinstance(full_name, str) else None
    email_norm = _normalize_email(str(email))
    record = {
        "id": uid,
        "email": email_norm,
        "full_name": full_name_norm,
        "password_hash": pwd_hash,
        "created_at": now,
    }
    if settings.data_provider == "sqlite":
        try:
            with sqlite_db.get_conn() as conn:
                sqlite_db.execute(
                    conn,
                    "INSERT INTO users (id, email, full_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                    (record["id"], record["email"], record["full_name"], record["password_hash"], record["created_at"]),
                )
        except sqlite3.IntegrityError:
            # Unique constraint violation (email)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        except sqlite3.OperationalError:
            # Likely bad DB path/locked schema/etc.
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database operation failed")
        except sqlite3.DatabaseError:
            # Broader database issues mapped to client error to avoid 500s in auth flows
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database operation failed")
    else:
        # Enforce unique email in-memory
        if email_norm in _mem_users_by_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        _mem_users[uid] = record
        _mem_users_by_email[email_norm] = uid
    return record


def _get_user_by_id(user_id: str) -> Optional[Dict]:
    settings = get_settings()
    if settings.data_provider == "sqlite":
        try:
            with sqlite_db.get_conn() as conn:
                row = sqlite_db.fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
                return row
        except sqlite3.OperationalError:
            # On DB read error during auth resolution, surface as generic not found to avoid leaking state
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database operation failed")
        except sqlite3.DatabaseError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Database operation failed")
    return _mem_users.get(user_id)


def _user_public(rec: Dict) -> UserPublic:
    return UserPublic(id=rec["id"], email=rec["email"], full_name=rec.get("full_name"))


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    """Dependency to extract current user from JWT token."""
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    rec = _get_user_by_id(sub)
    if not rec:
        raise HTTPException(status_code=401, detail="User not found")
    return _user_public(rec)


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
    description="Create a new user account.",
)
def register(payload: UserCreate):
    """Register a new user with hashed password.

    Returns:
        201 with public user if created.
        409 if email already exists.
        400 if validation fails.
    """
    email_norm = _normalize_email(str(payload.email))
    existing = _get_user_by_email(email_norm)
    if existing:
        # Use 409 Conflict for duplicate resource
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    try:
        pwd_hash = hash_password(payload.password)
    except ValueError as ve:
        # Input policy violation (e.g., too short)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception:
        # Any unexpected hashing/backend error -> 400 to avoid 500s in auth
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password")
    rec = _create_user(email_norm, payload.full_name, pwd_hash)
    return _user_public(rec)


# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenResponse, summary="Login", description="Authenticate and receive an access token.")
def login(payload: UserLogin):
    """Authenticate a user and return a JWT access token."""
    rec = _get_user_by_email(payload.email)
    if not rec:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, rec["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=rec["id"], claims={"email": rec["email"]})
    return TokenResponse(access_token=token)


# PUBLIC_INTERFACE
@router.get("/me", response_model=MeResponse, summary="Current user", description="Return the current authenticated user.")
def me(current: UserPublic = Depends(get_current_user)):
    """Return current user data."""
    return MeResponse(**current.model_dump())
