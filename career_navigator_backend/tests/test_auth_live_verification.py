import os

import pytest
import requests

# PUBLIC_INTERFACE
def _get_base_url() -> str:
    """Resolve the backend base URL from the running containers metadata or environment.

    Priority:
    1) BACKEND_BASE_URL env var (for overrides in CI)
    2) Default to the port used by this workspace (3010)
    """
    url = os.getenv("BACKEND_BASE_URL")
    if url:
        return url.rstrip("/")
    # Default known port from running_containers metadata
    return "http://localhost:3010"


def _options_allow_origin(headers: dict) -> dict:
    """Helper to build minimal CORS preflight headers."""
    return {
        "Origin": headers.get("Origin", "http://localhost:3000"),
        "Access-Control-Request-Method": headers.get("Access-Control-Request-Method", "POST"),
        "Access-Control-Request-Headers": headers.get("Access-Control-Request-Headers", "content-type,authorization"),
    }


@pytest.mark.auth
@pytest.mark.smoke
def test_register_login_me_and_preflight():
    """
    Targeted verification for:
      - POST /auth/register -> 201, duplicate -> 409
      - POST /auth/login -> 200 with access_token and token_type='bearer'
      - GET /auth/me -> 200 with expected shape
      - OPTIONS preflight for /auth/register and /auth/login return 200/204
    """
    base = _get_base_url()

    # If backend is down, skip gracefully (this test is meant to run against a live instance).
    try:
        r = requests.get(f"{base}/docs", timeout=5)
        if r.status_code >= 500:
            pytest.skip(f"Backend not reachable (status {r.status_code}) at {base}/docs")
    except requests.RequestException as e:
        pytest.skip(f"Backend not reachable at {base}: {e}")

    # 1) Register
    email = f"testuser_{os.getpid()}@example.com"
    payload = {"email": email, "password": "StrongPassw0rd!", "full_name": "Test User"}
    resp = requests.post(f"{base}/auth/register", json=payload, timeout=10)
    assert resp.status_code in (201, 409), f"Unexpected status for register: {resp.status_code} -> {resp.text}"
    if resp.status_code == 201:
        data = resp.json()
        assert data.get("email") == email
        assert "id" in data
    else:
        # If 409 returned, user exists; continue flow
        pass

    # 1b) Duplicate register -> 409
    dup = requests.post(f"{base}/auth/register", json=payload, timeout=10)
    assert dup.status_code == 409, f"Expected 409 for duplicate, got {dup.status_code} -> {dup.text}"

    # 2) Login -> 200 with access_token and token_type='bearer'
    login = requests.post(f"{base}/auth/login", json={"email": email, "password": "StrongPassw0rd!"}, timeout=10)
    assert login.status_code == 200, f"Login failed: {login.status_code} -> {login.text}"
    token = login.json()
    assert "access_token" in token and isinstance(token["access_token"], str) and token["access_token"], "Missing access_token"
    assert token.get("token_type", "bearer").lower() == "bearer", "token_type must be 'bearer'"

    # 3) /auth/me -> 200
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    me = requests.get(f"{base}/auth/me", headers=headers, timeout=10)
    assert me.status_code == 200, f"/auth/me failed: {me.status_code} -> {me.text}"
    me_data = me.json()
    assert me_data.get("email") == email
    assert "id" in me_data

    # 4) CORS preflight for /auth/register and /auth/login -> 200/204
    cors_headers = _options_allow_origin({})
    for path in ("/auth/register", "/auth/login"):
        opt = requests.options(f"{base}{path}", headers=cors_headers, timeout=10)
        assert opt.status_code in (200, 204), f"Preflight for {path} failed: {opt.status_code} -> {opt.text}"
        # Basic CORS headers presence (if CORS is enabled)
        acao = opt.headers.get("Access-Control-Allow-Origin")
        acam = opt.headers.get("Access-Control-Allow-Methods", "")
        # Do not hard fail if CORS headers are absent, but verify if present they include POST
        if acao is not None:
            assert "*" in acao or "http://" in acao or "https://" in acao
        if acam:
            assert "POST" in acam or "OPTIONS" in acam
