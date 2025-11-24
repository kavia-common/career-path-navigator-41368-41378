# Developer Testing Notes

Some tests (e.g., smoke tests) expect the FastAPI server to be running at `http://127.0.0.1:8000`.

To run locally:

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
