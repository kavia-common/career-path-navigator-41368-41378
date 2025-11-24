from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
import sqlite3

from src.core.config import get_settings
from src.routers import health, auth, datasets, roles, competencies, adjacency, resources, recommendations, jobs, progress

settings = get_settings()

app = FastAPI(
    title="Career Navigator Backend",
    description="APIs for authentication, datasets, recommendations, jobs, and progress.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Service health"},
        {"name": "auth", "description": "Authentication"},
        {"name": "datasets", "description": "Raw dataset files"},
        {"name": "roles", "description": "Roles catalog"},
        {"name": "competencies", "description": "Competency taxonomy"},
        {"name": "adjacency", "description": "Role adjacency datasets"},
        {"name": "resources", "description": "Learning/reference resources"},
        {"name": "recommendations", "description": "Role recommendations"},
        {"name": "jobs", "description": "Job tracking"},
        {"name": "progress", "description": "User progress tracking"},
    ],
)

# Install CORS middleware early so that OPTIONS preflight is handled
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # keep True to allow cookies/Authorization headers if needed
    allow_methods=["*"],     # include OPTIONS automatically
    allow_headers=["*"],     # include requested custom headers
)

# Exception handlers (structured, no sensitive details)
@app.exception_handler(sqlite3.DatabaseError)
async def sqlite_error_handler(request: Request, exc: sqlite3.DatabaseError):
    # Map sqlite operational/db errors to 400 to avoid 500s in auth flows or simple persistence actions
    return JSONResponse(status_code=400, content={"detail": "Database operation failed"})

# Ensure standard HTTP exceptions pass through (do not override FastAPI/Starlette defaults)
@app.exception_handler(StarletteHTTPException)
async def http_exception_passthrough(request: Request, exc: StarletteHTTPException):
    # Let FastAPI build the normal response (status + detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Do not treat validation errors from OPTIONS as 500s; keep default 422 for non-OPTIONS requests
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # If it's a CORS preflight (OPTIONS), respond with empty OK to avoid 400/422 from body validation
    if request.method.upper() == "OPTIONS":
        # Let CORSMiddleware handle headers; return 204 No Content
        return JSONResponse(status_code=204, content=None)
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Catch-all for truly unhandled exceptions only
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(roles.router)
app.include_router(competencies.router)
app.include_router(adjacency.router)
app.include_router(resources.router)
app.include_router(recommendations.router)
app.include_router(jobs.router)
app.include_router(progress.router)
