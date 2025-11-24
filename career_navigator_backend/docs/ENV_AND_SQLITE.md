# Backend Environment and SQLite Configuration

This service uses SQLite by default to avoid in-memory loss and to ensure /auth/register, /auth/login, and /auth/me work end-to-end.

Defaults:
- DATA_PROVIDER=sqlite
- DB_PATH resolves to ../../career_navigator_database/myapp.db (sibling container) or falls back to a local myapp.db under the backend workspace if the sibling directory is absent.

Override via .env:
- See .env.example. You may set:
  - DATA_PROVIDER=sqlite|json
  - DB_PATH=/absolute/or/relative/path/to/myapp.db
    - In this workspace, the database container path is:
      /home/kavia/workspace/code-generation/career-path-navigator-41368-41377/career_navigator_database/myapp.db
  - JWT_SECRET (required for non-dev)
  - CORS_ORIGINS (CSV)

Password hashing and bcrypt 72-byte limit:
- The service safely supports passwords longer than 72 bytes by pre-hashing with SHA-256 and then hashing with bcrypt.
- Stored hashes created for long passwords are tagged internally and verified accordingly.
- Existing shorter-password bcrypt hashes remain compatible.

bcrypt/passlib compatibility notes:
- We pin passlib[bcrypt]==1.7.4 and bcrypt==4.0.1 to avoid a known incompatibility causing:
  AttributeError: module 'bcrypt' has no attribute '__about__'
- The security module prefers passlib's bcrypt handlers; if a C backend is unavailable/problematic,
  passlib will transparently use its pure-Python bcrypt implementation.
- If passlib cannot be imported at all, the system falls back to salted SHA-256 (dev-only) and continues to function.

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
- If you encounter bcrypt import errors in other environments, confirm the pinned versions above or allow the passlib pure-Python fallback.
