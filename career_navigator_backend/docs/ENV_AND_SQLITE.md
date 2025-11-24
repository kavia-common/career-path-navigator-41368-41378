# Backend Environment and SQLite Configuration

This service uses SQLite by default to avoid in-memory loss and to ensure /auth/register, /auth/login, and /auth/me work end-to-end.

Defaults:
- DATA_PROVIDER=sqlite
- DB_PATH resolves to ../../career_navigator_database/myapp.db (sibling container) or falls back to a local myapp.db under the backend workspace if the sibling directory is absent.

Override via .env:
- See .env.example. You may set:
  - DATA_PROVIDER=sqlite|json
  - DB_PATH=/absolute/or/relative/path/to/myapp.db
  - JWT_SECRET (required for non-dev)
  - CORS_ORIGINS (CSV)

Operational Error Handling:
- Duplicate email on register → 409 Conflict
- SQLite Operational errors (e.g., locked DB, path invalid) → 400 Bad Request (no stack traces)
- Invalid credentials → 401 Unauthorized

Smoke test with SQLite:
1) POST /auth/register {"email":"user@example.com","password":"StrongPassw0rd!","full_name":"User"}
   - Expect 201, response contains id, email (lowercased).
2) POST /auth/login {"email":"user@example.com","password":"StrongPassw0rd!"}
   - Expect 200, token in access_token.
3) GET /auth/me with Authorization: Bearer <token>
   - Expect 200 with id and email.

Troubleshooting:
- Ensure DB_PATH directory exists and is writable by the app. The service will create the directory if missing.
- If you see 400 "Database operation failed", verify DB_PATH and file permissions or remove any corrupted db file and retry.
