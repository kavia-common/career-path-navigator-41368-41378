from fastapi.testclient import TestClient
from pathlib import Path

from src.api.main import app
from src.routers import auth as auth_router
from src.core.config import reset_settings_cache

client = TestClient(app)


def test_register_login_with_requested_sqlite_env(monkeypatch):
    """
    Validate auth endpoints using the specific environment requested:
    DATA_PROVIDER=sqlite
    DB_PATH=/home/kavia/workspace/code-generation/career-path-navigator-41368-41377/career_navigator_database/myapp.db
    The DB path is shared across runs; tests rely on reset_auth_state() to clear user tables.
    """
    db_path = "/home/kavia/workspace/code-generation/career-path-navigator-41368-41377/career_navigator_database/myapp.db"
    # Ensure parent directory exists; the app will create it if missing but we don't create files here.
    parent = Path(db_path).parent
    assert parent.is_dir(), f"Expected DB parent directory to exist: {parent}"

    # Apply env
    monkeypatch.setenv("DATA_PROVIDER", "sqlite")
    monkeypatch.setenv("DB_PATH", db_path)

    # Ensure clean state and reload settings to pick up env
    reset_settings_cache()
    auth_router.reset_auth_state()

    email = "sqlite_env_user@example.com"
    password = "StrongPassw0rd!"
    full_name = "SQLite Env User"

    # Register should return 201
    r = client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["email"] == email.lower()
    assert "id" in user

    # Duplicate should return 409
    r2 = client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})
    assert r2.status_code == 409, r2.text

    # Login should return 200 with access_token
    r3 = client.post("/auth/login", json={"email": email, "password": password})
    assert r3.status_code == 200, r3.text
    token_payload = r3.json()
    token = token_payload.get("access_token")
    assert token and isinstance(token, str)
    assert token_payload.get("token_type") == "bearer"

    # /auth/me should return 200
    r4 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 200, r4.text
    me = r4.json()
    assert me["email"] == email.lower()
    assert me["id"] == user["id"]
