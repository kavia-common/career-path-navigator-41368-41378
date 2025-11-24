import os
import uuid
import pytest
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # type: ignore

# Disable only for smoke checks; do not do this for production clients.
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def _base() -> str:
    return os.environ.get("CAREER_BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _json(session: requests.Session, method: str, path: str, token: str | None = None, body: dict | None = None) -> requests.Response:
    url = f"{_base()}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return session.request(method=method, url=url, json=body, headers=headers, timeout=20, verify=False)


@pytest.mark.smoke
def test_openapi_route_present_and_json():
    sess = requests.Session()
    r = _json(sess, "GET", "/interfaces/openapi.json")
    assert r.status_code == 200, f"OpenAPI route missing: {r.status_code} {r.text[:200]}"
    assert r.headers.get("content-type", "").startswith("application/json"), "OpenAPI should be JSON"
    data = r.json()
    assert "openapi" in data and "paths" in data, "Invalid OpenAPI payload"


@pytest.mark.smoke
def test_auth_protected_jobs_and_progress_flow():
    sess = requests.Session()
    # Register a unique user
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassw0rd!"
    r = _json(sess, "POST", "/auth/register", body={"email": email, "password": password, "full_name": "T User"})
    assert r.status_code in (201, 409), f"Register failed: {r.status_code} {r.text}"
    # Login
    r = _json(sess, "POST", "/auth/login", body={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token")
    assert token, "No token returned"

    # Jobs list initially empty
    r = _json(sess, "GET", "/jobs/", token=token)
    assert r.status_code == 200, f"Jobs GET failed: {r.status_code} {r.text}"
    assert isinstance(r.json(), list), "Jobs should be a list"

    # Add a job
    job_payload = {"title": "Senior Engineer", "company": "Acme", "status": "applied", "notes": "via referral"}
    r = _json(sess, "POST", "/jobs/", token=token, body=job_payload)
    assert r.status_code == 201, f"Jobs POST failed: {r.status_code} {r.text}"
    job = r.json()
    assert job.get("title") == "Senior Engineer"
    # List again should contain at least one
    r = _json(sess, "GET", "/jobs/", token=token)
    assert r.status_code == 200 and len(r.json()) >= 1

    # Progress list initially empty
    r = _json(sess, "GET", "/progress/", token=token)
    assert r.status_code == 200, f"Progress GET failed: {r.status_code} {r.text}"
    assert isinstance(r.json(), list), "Progress should be a list"

    # Add a progress item
    prog_payload = {"competency": "Architecture", "level": "A", "evidence_url": None}
    r = _json(sess, "POST", "/progress/", token=token, body=prog_payload)
    assert r.status_code == 201, f"Progress POST failed: {r.status_code} {r.text}"
    prog = r.json()
    assert prog.get("competency") == "Architecture"
    # List again should contain at least one
    r = _json(sess, "GET", "/progress/", token=token)
    assert r.status_code == 200 and len(r.json()) >= 1
