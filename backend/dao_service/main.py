"""FastAPI application entry point."""

from fastapi import FastAPI
from sqlalchemy import text

from dao_service.api.v1 import (
    conversations_api,
    demo_flags_api,
    goals_api,
    milestones_api,
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
        {"name": "milestones", "description": "Milestone management"},
        {"name": "conversations", "description": "Conversation history"},
        {"name": "demo-flags", "description": "Demo/simulation flags"},
    ],
)

# Mount v1 routers
app.include_router(users_api.router, prefix="/api/v1")
app.include_router(goals_api.router, prefix="/api/v1")
app.include_router(tasks_api.router, prefix="/api/v1")
app.include_router(milestones_api.router, prefix="/api/v1")
app.include_router(conversations_api.router, prefix="/api/v1")
app.include_router(demo_flags_api.router, prefix="/api/v1")


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
