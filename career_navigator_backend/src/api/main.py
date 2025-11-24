from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# CORS to allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers (structured, no sensitive details)
@app.exception_handler(sqlite3.DatabaseError)
async def sqlite_error_handler(request: Request, exc: sqlite3.DatabaseError):
    # Map sqlite operational/db errors to 400 to avoid 500s in auth flows or simple persistence actions
    return JSONResponse(status_code=400, content={"detail": "Database operation failed"})

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
