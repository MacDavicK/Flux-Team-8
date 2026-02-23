"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from dao_service.api.v1 import (
    conversations_api,
    goals_api,
    notification_log_api,
    patterns_api,
    tasks_api,
    users_api,
)
from dao_service.core.database import _get_session_factory

app = FastAPI(
    title="Flux Data Access API",
    description="Framework-agnostic data persistence microservice for Flux AI agents",
    version="1.0.0",
    openapi_tags=[
        {"name": "users", "description": "User operations"},
        {"name": "goals", "description": "Goal management"},
        {"name": "tasks", "description": "Task operations (includes Scheduler & Observer endpoints)"},
        {"name": "conversations", "description": "Conversation history"},
        {"name": "patterns", "description": "Behavioral pattern signals"},
        {"name": "notification-log", "description": "Notification delivery logs"},
    ],
)

# --- Exception handlers ---


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Return 409 Conflict for unique/FK constraint violations instead of 500."""
    return JSONResponse(
        status_code=409,
        content={"detail": "A resource with a conflicting unique constraint already exists."},
    )


# Mount v1 routers
app.include_router(users_api.router, prefix="/api/v1")
app.include_router(goals_api.router, prefix="/api/v1")
app.include_router(tasks_api.router, prefix="/api/v1")
app.include_router(conversations_api.router, prefix="/api/v1")
app.include_router(patterns_api.router, prefix="/api/v1")
app.include_router(notification_log_api.router, prefix="/api/v1")


# --- Operational endpoints ---


@app.get("/health", tags=["operations"])
async def health():
    """Liveness probe — always returns OK if the process is running."""
    return {"status": "ok"}


@app.get("/ready", tags=["operations"])
async def ready():
    """Readiness probe — verifies database connectivity."""
    try:
        async with _get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "detail": str(e)}
