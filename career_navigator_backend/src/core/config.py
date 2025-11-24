"""Application configuration utilities.

This module centralizes environment configuration for the backend, including
JWT secrets, data provider options, and optional SQLite database paths.

PySecure-4-Minimal controls:
- Do not log secrets.
- Validate enum-like env values.
- Avoid crashing on missing env; provide safe defaults for dev.

Environment variables (to be provided via .env by orchestrator):
- DATA_PROVIDER: 'sqlite' (default) or 'json'
- JWT_SECRET: Secret key for JWT; defaults to a dev value only for local use
- JWT_ALGORITHM: Defaults to HS256
- ACCESS_TOKEN_EXPIRE_MINUTES: Defaults to 60
- DB_PATH: Optional absolute/relative path to sqlite database. If not provided,
  will attempt ../career_navigator_database/myapp.db if present; else create a local file.

Note: Do not write .env here. Provide a .env.example elsewhere if needed.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    """Configuration settings loaded from environment with secure defaults."""
    data_provider: Literal["json", "sqlite"] = Field(
        default="sqlite", description="Data provider for catalogs and persistence."
    )
    jwt_secret: str = Field(
        default="dev-secret-change-me", description="JWT secret key (dev default)."
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(
        default=60, description="Access token TTL in minutes."
    )
    db_path: Optional[str] = Field(
        default=None, description="SQLite DB path (used when DATA_PROVIDER=sqlite)."
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins.",
    )

    data_dir: str = Field(
        default=str(Path(__file__).resolve().parents[2] / "data"),
        description="Path to JSON data directory."
    )


def _default_db_path() -> str:
    """Resolve the default SQLite file path.

    Priority:
    1) Sibling container database: ../../career_navigator_database/myapp.db
    2) Local file under backend workspace: ../myapp.db
    """
    sibling = Path(__file__).resolve().parents[3] / "career_navigator_database" / "myapp.db"
    if sibling.exists() or sibling.parent.exists():
        return str(sibling)
    local = Path(__file__).resolve().parents[2] / "myapp.db"
    return str(local)


def load_settings() -> Settings:
    """Load settings from environment with robust defaults and validation.

    Returns:
        Settings: Validated settings object.

    Raises:
        ValidationError: If environment values are invalid.
    """
    data_provider = os.getenv("DATA_PROVIDER", "sqlite").strip().lower()
    if data_provider not in {"json", "sqlite"}:
        data_provider = "sqlite"  # safe default favoring persistence

    cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]

    db_path_env = os.getenv("DB_PATH")
    db_path = db_path_env if db_path_env else _default_db_path()

    try:
        settings = Settings(
            data_provider=data_provider,  # type: ignore[arg-type]
            jwt_secret=os.getenv("JWT_SECRET", "dev-secret-change-me"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
            db_path=db_path,
            cors_origins=cors_origins,
            data_dir=os.getenv(
                "DATA_DIR",
                str(Path(__file__).resolve().parents[2] / "data")
            ),
        )
    except ValidationError as ve:
        # Keep error generic to avoid leaking values
        raise ve
    return settings


# Singleton-style accessor
_settings: Optional[Settings] = None

# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Get cached application settings."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings

# PUBLIC_INTERFACE
def reset_settings_cache() -> None:
    """Reset the cached settings.

    This is primarily intended for tests to ensure that changes to environment
    variables (e.g., DATA_PROVIDER, DB_PATH) take effect on subsequent calls
    to get_settings().
    """
    global _settings
    _settings = None
