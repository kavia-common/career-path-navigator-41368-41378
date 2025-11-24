"""Security utilities for JWT auth and password hashing.

Uses passlib[bcrypt] with safe fallbacks:
- Prefer passlib's bcrypt handlers; if the C extension import is problematic
  (e.g., AttributeError: module 'bcrypt' has no attribute '__about__'),
  fall back to passlib's pure-Python bcrypt backend transparently.
- If passlib is unavailable entirely, use salted SHA-256 (dev-only).

Pre-hashing policy:
- To avoid bcrypt's 72-byte input limit, we pre-hash long passwords using SHA-256
  and tag stored hashes as "bcrypt-sha256$<bcrypt-hash>" so verification can
  handle both legacy and new formats.

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

# Robust passlib import with bcrypt handler fallback selection.
_pwd_context: Optional["CryptContext"] = None
try:
    # Prefer passlib's bcrypt handler and explicitly prefer builtin (pure-python) backend to avoid C-extension issues.
    import os
    os.environ.setdefault("PASSLIB_BUILTIN_BCRYPT", "1")

    from passlib.context import CryptContext  # type: ignore
    from passlib.handlers import bcrypt as passlib_bcrypt  # type: ignore

    # Touch attribute to ensure import path is valid without reading external package internals.
    _ = getattr(passlib_bcrypt, "__name__", "passlib.handlers.bcrypt")

    # Build a context that prefers bcrypt. With PASSLIB_BUILTIN_BCRYPT=1, passlib will use its internal backend.
    _pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
    )
except Exception:
    # If passlib import/initialization fails, gracefully degrade to salted SHA-256.
    _pwd_context = None

from src.core.config import get_settings


def _sha256_hex(s: str) -> str:
    """
    Return a hex-encoded SHA-256 digest of the provided string using UTF-8.
    This is used to pre-hash long passwords to safely fit bcrypt's 72-byte limit.
    """
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _bcrypt_safe_transform(pw: str) -> str:
    """
    Transform the password so bcrypt always sees a short, fixed-length input:
    - If password length <= 72 bytes (utf-8), use as-is (after stripping accidental whitespace).
    - If > 72 bytes, pre-hash with SHA-256, hex-encode (64 chars), then bcrypt that string.

    This ensures:
    - No silent truncation in bcrypt.
    - Users with long passwords can authenticate reliably.
    - Backwards-compatibility for existing bcrypt hashes created without pre-hashing (we support both on verify).
    """
    if not isinstance(pw, str):
        raise ValueError("Password must be a string.")
    trimmed = pw.strip()
    b = trimmed.encode("utf-8")
    if len(b) <= 72:
        return trimmed
    # Pre-hash and return hex (64 chars ASCII)
    return _sha256_hex(trimmed)


def _is_sha256_bcrypt_tagged(hashed: str) -> bool:
    """Detect our scheme tag for pre-hashed bcrypt format."""
    return isinstance(hashed, str) and hashed.startswith("bcrypt-sha256$")


def _wrap_bcrypt(hashed_core: str) -> str:
    """Wrap a bcrypt hash core with our scheme tag for storage."""
    return f"bcrypt-sha256${hashed_core}"


def _unwrap_bcrypt(hashed: str) -> str:
    """Extract the underlying bcrypt hash from a tagged bcrypt-sha256 string."""
    return hashed.split("$", 1)[1]


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """
    PUBLIC_INTERFACE
    Hash a password securely.

    Strategy:
    - For bcrypt: If the raw password >72 bytes when utf-8 encoded, pre-hash with SHA-256 (hex) then bcrypt.
      We store the bcrypt result with a "bcrypt-sha256$" tag to indicate pre-hashing.
      If <=72 bytes, we bcrypt the raw password without pre-hashing.
    - Fallback: salted SHA-256 for environments without passlib (dev-only).

    Raises:
        ValueError: If password policy fails.
    """
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    if _pwd_context:
        transformed = _bcrypt_safe_transform(password)
        hashed_core = _pwd_context.hash(transformed)
        # Tag if we had to pre-hash (i.e., original utf-8 length > 72)
        if len(password.strip().encode("utf-8")) > 72:
            return _wrap_bcrypt(hashed_core)
        return hashed_core

    # Fallback: salted sha256 (not recommended for production)
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


# PUBLIC_INTERFACE
def verify_password(password: str, hashed: str) -> bool:
    """
    PUBLIC_INTERFACE
    Verify a password against a stored hash.

    Supports:
    - New scheme "bcrypt-sha256$<bcrypt>": pre-hash candidate then verify with bcrypt.
    - Legacy plain bcrypt (no tag): verify the candidate directly (no pre-hash),
      with a second attempt using pre-hashed candidate for compatibility.
    - Fallback "sha256$<salt>$<digest>": salted sha-256 comparison.
    """
    # bcrypt available and hash is not fallback sha256
    if _pwd_context and hashed and not hashed.startswith("sha256$"):
        try:
            if _is_sha256_bcrypt_tagged(hashed):
                bcrypt_part = _unwrap_bcrypt(hashed)
                candidate = _sha256_hex(password.strip())
                return _pwd_context.verify(candidate, bcrypt_part)

            # Legacy bcrypt (no tag). For compatibility, attempt direct verify on raw and then pre-hashed if direct fails.
            if _pwd_context.verify(password.strip(), hashed):
                return True
            candidate_ph = _sha256_hex(password.strip())
            return _pwd_context.verify(candidate_ph, hashed)
        except Exception:
            # Any verify error yields False
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
    """
    PUBLIC_INTERFACE
    Create a signed JWT access token.

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
        for k, v in claims.items():
            if k not in {"sub", "iat", "exp"}:
                to_encode[k] = v
    token = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


# PUBLIC_INTERFACE
def decode_token(token: str) -> dict[str, Any]:
    """
    PUBLIC_INTERFACE
    Decode and validate a JWT token, returning claims.

    Raises:
        JWTError: If token is invalid or expired.
    """
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
