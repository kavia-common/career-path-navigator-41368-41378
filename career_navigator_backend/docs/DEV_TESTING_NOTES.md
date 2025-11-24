# Developer Testing Notes

Some tests (e.g., smoke tests) expect the FastAPI server to be running. You can run locally with uvicorn:

```bash
# From the backend folder
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Then, in a separate terminal, run the tests:

```bash
pytest -q
```

These tests validate:
- Auth endpoints with SQLite using the shared DB path
  - POST /auth/register -> 201
  - Duplicate register -> 409
  - POST /auth/login -> 200 with `access_token` and `token_type=bearer`
  - GET /auth/me -> 200
- CORS preflight OPTIONS for /auth/login and /auth/register returns 200/204
- Datasets and recommendations smoke endpoints

If running in CI, ensure the service is started before executing the smoke tests, or use a test configuration that mocks HTTP calls.

## Live auth verification

A focused live verification test is available to validate:
- POST /auth/register -> 201 on first create, 409 on duplicate
- POST /auth/login -> 200 and returns access_token with token_type=bearer
- GET /auth/me -> 200
- OPTIONS preflight for /auth/register and /auth/login returns 200/204

Usage:
- Backend up locally at http://localhost:3010 or http://127.0.0.1:8000
- Or set env var BACKEND_BASE_URL to point at a remote instance

Run:
```bash
# local default (port 3010)
pytest -q -k test_auth_live_verification -m auth

# against remote/live URL
BACKEND_BASE_URL="https://vscode-internal-30268-beta.beta01.cloud.kavia.ai:3010" pytest -q -k test_auth_live_verification -m auth
```

This test will skip automatically if the backend is not reachable to avoid false negatives in CI when the service is down.
