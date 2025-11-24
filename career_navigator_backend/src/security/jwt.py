"""Security utilities for JWT auth and password hashing.

Uses passlib[bcrypt] if available; otherwise falls back to hashlib+salt with
a clear comment that it's not recommended for production.

PySecure-4-Minimal controls:
- Use constant-time comparisons where applicable.
- Avoid logging secrets.
- Deterministic, validated token generation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import hmac
import hashlib
import secrets

from jose import jwt  # python-jose (fastapi-compatible)
# Note: python-jose is not in requirements yet; we'll implement a minimal HS256 via jose
# If import fails in CI, we will fallback to PyJWT or implement manual signer.

try:
    from passlib.context import CryptContext  # type: ignore
    _pwd_context: Optional[CryptContext] = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:  # pragma: no cover - fallback when passlib not installed
    _pwd_context = None

from src.core.config import get_settings


def _bcrypt_safe_normalize(pw: str) -> str:
    """
    Normalize and safely limit password for bcrypt which only considers first 72 bytes.
    We:
    - Strip leading/trailing whitespace (not security-sensitive here, but avoids accidental spaces)
    - Encode to utf-8 and truncate to 72 bytes boundary
    - Decode back to utf-8 with errors='ignore' to ensure compatibility
    Note: This mirrors effective bcrypt semantics and avoids runtime ValueError from some backends.
    """
    if not isinstance(pw, str):
        raise ValueError("Password must be a string.")
    trimmed = pw.strip()
    b = trimmed.encode("utf-8")
    limited = b[:72]
    return limited.decode("utf-8", errors="ignore")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a password securely.

    If passlib is available, use bcrypt. Otherwise, use salted SHA-256 (not recommended for prod).
    Controls:
    - Enforce minimum length
    - Normalize/truncate to 72 bytes for bcrypt to prevent backend errors and undefined behavior
    """
    if not isinstance(password, str) or len(password) < 8:
        # Basic validation; real policies can be stricter
        raise ValueError("Password must be at least 8 characters.")
    if _pwd_context:
        # Normalize for bcrypt 72-byte constraint
        normalized = _bcrypt_safe_normalize(password)
        return _pwd_context.hash(normalized)
    # Fallback: salted sha256
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


# PUBLIC_INTERFACE
def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a stored hash.

    When using bcrypt, apply the same normalization/truncation as during hashing to ensure consistency.
    """
    if _pwd_context and hashed and not hashed.startswith("sha256$"):
        try:
            normalized = _bcrypt_safe_normalize(password)
            return _pwd_context.verify(normalized, hashed)
        except Exception:
            return False
    # Fallback verify for salted sha256
    try:
        _, salt, digest = hashed.split("$", 2)
    except ValueError:
        return False
    calc = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(calc, digest)


# PUBLIC_INTERFACE
def create_access_token(subject: str, expires_minutes: Optional[int] = None, claims: Optional[dict[str, Any]] = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The subject/user identifier.
        expires_minutes: TTL override; if None, use settings.
        claims: Additional claims to include.

    Returns:
        A compact JWT string.
    """
    settings = get_settings()
    exp_minutes = expires_minutes if isinstance(expires_minutes, int) and expires_minutes > 0 else settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    to_encode: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    if isinstance(claims, dict):
        # Avoid overwriting reserved claims
        for k, v in claims.items():
            if k not in {"sub", "iat", "exp"}:
                to_encode[k] = v
    token = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


# PUBLIC_INTERFACE
def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token, returning claims.

    Raises:
        JWTError: If token is invalid or expired.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
