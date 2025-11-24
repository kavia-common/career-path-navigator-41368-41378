from fastapi.testclient import TestClient

from src.api.main import app
from src.routers import auth as auth_router
from src.core.config import reset_settings_cache

client = TestClient(app)


def _register_and_login(email: str, full_name: str | None = None, password: str = "StrongPassw0rd!"):
    # Ensure clean in-memory state (no-op for sqlite)
    auth_router.reset_auth_state()

    # CORS preflight smoke (OPTIONS) for auth routes should not error (middleware handles it)
    for path, method in [("/auth/register", "POST"), ("/auth/login", "POST"), ("/auth/me", "GET")]:
        pre = client.options(path, headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": method})
        assert pre.status_code in (200, 204)

    # Register
    r = client.post("/auth/register", json={"email": email, "full_name": full_name, "password": password})
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["email"] == email.lower()
    assert "id" in user

    # Duplicate should 409
    r2 = client.post("/auth/register", json={"email": email, "full_name": full_name, "password": password})
    assert r2.status_code == 409, r2.text

    # Login
    r3 = client.post("/auth/login", json={"email": email, "password": password})
    assert r3.status_code == 200, r3.text
    token_payload = r3.json()
    token = token_payload["access_token"]
    # token_type should be 'bearer' by contract
    assert token_payload.get("token_type") == "bearer"

    # Me
    r4 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 200, r4.text
    me = r4.json()
    assert me["email"] == email.lower()
    assert me["id"] == user["id"]


def test_register_login_json_provider(monkeypatch, tmp_path):
    # Ensure default JSON provider
    monkeypatch.delenv("DATA_PROVIDER", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)
    reset_settings_cache()
    auth_router.reset_auth_state()
    _register_and_login("User1@example.com", "User One")


def test_register_login_sqlite_provider(monkeypatch, tmp_path):
    # Force sqlite provider with temp db
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATA_PROVIDER", "sqlite")
    monkeypatch.setenv("DB_PATH", str(db_path))
    reset_settings_cache()
    auth_router.reset_auth_state()
    _register_and_login("User2@example.com", "User Two")
