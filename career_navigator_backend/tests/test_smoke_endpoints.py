import os
import typing as t

import pytest
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # type: ignore

# Disable only for smoke checks; do not do this for production clients.
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def _get_base_url() -> str:
    """
    Determine base URL for smoke tests:
    - CAREER_BACKEND_BASE_URL env var if provided (e.g., https://host:port)
    - else default to http://127.0.0.1:8000 for local uvicorn
    """
    return os.environ.get("CAREER_BACKEND_BASE_URL", "http://127.0.0.1:8000")


def _check_get(session: requests.Session, path: str, expect_nonempty: bool = False) -> t.Tuple[int, t.Any]:
    """
    Helper to GET an endpoint and minimally validate:
    - not a 5xx
    - JSON parseable
    - non-empty when requested
    Returns: (status_code, parsed_json)
    """
    base = _get_base_url().rstrip("/")
    url = f"{base}{path}"
    r = session.get(url, timeout=15, verify=False)
    assert r.status_code < 500, f"500+ on {path}: {r.status_code} body={r.text[:500]}"
    try:
        data = r.json()
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"Non-JSON response for {path}: {exc}\nBody: {r.text[:500]}")
    if expect_nonempty:
        assert data and (not isinstance(data, dict) or len(data) > 0), f"Empty payload for {path}"
    return r.status_code, data


@pytest.mark.smoke
def test_health_and_datasets_and_recommendations_endpoints_smoke():
    """
    Basic smoke across core MVP:
    1) GET /datasets/, and /roles, /competencies, /adjacency, /resources routers respond 2xx and return data when applicable
    2) GET /recommendations/for-ca returns non-empty recommendations
    3) No 5xx responses
    """
    sess = requests.Session()

    # Root health
    code, data = _check_get(sess, "/", expect_nonempty=True)
    assert code == 200, f"Unexpected / status {code}"
    # Datasets index should be non-empty (data files exist)
    code, data = _check_get(sess, "/datasets/", expect_nonempty=True)
    assert code == 200

    # Check individual routers (without strict non-empty except where meaningful)
    endpoints = [
        "/roles/",
        "/competencies/definitions",
        "/competencies/matrix",
        "/adjacency/vs-ca",
        "/adjacency/matrix",
        "/resources/",
    ]
    for ep in endpoints:
        c, d = _check_get(sess, ep, expect_nonempty=False)
        assert c == 200, f"{ep} failed with {c}"
        # Minimal acceptance: JSON payload
        assert d is not None, f"{ep} returned null"

    # Recommendations (CA) should be non-empty list within top-N
    c, d = _check_get(sess, "/recommendations/for-ca?min_overlap=40&limit=5", expect_nonempty=True)
    assert c == 200
    assert isinstance(d, list), "Recommendations expected to be a list"
    assert len(d) > 0, "Recommendations list is empty"
