# Endpoint Contract Audit and Remediation - Changelog

Date: 2025-11-24

Scope:
- Backend container: career_navigator_backend
- Frontend container: career_navigator_frontend

Summary:
- Audited live/static OpenAPI and source routers.
- Compared all frontend ApiClient calls to backend routes.
- No path/method/parameter mismatches found.
- Added a stable route to serve the static OpenAPI JSON and smoke tests for contract verification.
- Validated SQLite ingestion paths for auth, jobs, and progress.

Backend routes (canonical):
- GET /  (health)
- POST /auth/register
- POST /auth/login
- GET /auth/me
- GET /datasets/
- GET /datasets/{name}
- GET /roles/
- GET /competencies/definitions
- GET /competencies/matrix
- GET /adjacency/vs-ca
- GET /adjacency/matrix
- GET /resources/
- GET /recommendations/for-ca?min_overlap&limit
- GET /jobs/  (Bearer)
- POST /jobs/ (Bearer)
- GET /progress/ (Bearer)
- POST /progress/ (Bearer)
- NEW: GET /interfaces/openapi.json (serve static OpenAPI JSON)
- NEW: GET /docs/usage (plain text usage notes)

Frontend ApiClient calls:
- Matches canonical endpoints exactly:
  - /auth/register, /auth/login, /auth/me
  - /datasets/, /roles/, /competencies/definitions, /competencies/matrix
  - /adjacency/vs-ca, /adjacency/matrix, /resources/
  - /recommendations/for-ca?min_overlap&limit
  - /jobs/ (GET/POST with Authorization header)
  - /progress/ (GET/POST with Authorization header)

OpenAPI:
- interfaces/openapi.json matches routers, including OAuth2 password flow (tokenUrl=/auth/login).
- NEW: Exposed at /interfaces/openapi.json to help consumers and tests fetch schema without filesystem access.

SQLite ingestion validation:
- Auth persisted to auth_users table; jobs and progress persisted to jobs and progress tables with user_id foreign key.
- Endpoints using DB: /auth/*, /jobs/*, /progress/* operate correctly when DATA_PROVIDER=sqlite.
- Data readers for datasets-only endpoints read from JSON datasets.

Smoke tests:
- tests/test_smoke_endpoints.py: public endpoints and recommendations.
- NEW tests/test_smoke_contracts.py: verifies OpenAPI route exists and end-to-end auth-protected flows for jobs and progress.

Notes:
- No environment variables embedded in code; base URL is set in frontend via REACT_APP_API_BASE.
- CORS configured via settings.cors_origins; OPTIONS handled gracefully.
