"""Pattern Observer Agent — FastAPI entrypoint (SCRUM-50).

Exposes:
  GET  /health
  POST /consult        — Goal Planner / Scheduler calls this
  POST /miss-signal    — Notifier Agent emits task-miss events here
  GET  /patterns/{uid} — Admin / debug: read stored patterns

Swagger UI:  http://localhost:8058/docs
ReDoc:       http://localhost:8058/redoc
OpenAPI JSON: http://localhost:8058/openapi.json
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from logger import get_logger
from routes import get_service, router

logger = get_logger("pattern_observer.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle hooks."""
    logger.info(
        "[Main] Starting %s v%s on port %d",
        settings.SERVICE_NAME,
        settings.SERVICE_VERSION,
        settings.PORT,
    )
    # Eagerly initialise the service so the first request is not slow
    get_service()
    logger.info("[Main] PatternService ready")
    yield
    # Shutdown — close HTTP client
    svc = get_service()
    await svc.close()
    logger.info("[Main] PatternService shut down cleanly")


app = FastAPI(
    title=settings.SERVICE_NAME,
    description=settings.SERVICE_DESCRIPTION,
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service liveness check.",
        },
        {
            "name": "Pattern Analysis",
            "description": (
                "Core Pattern Observer endpoints. "
                "Consume task-miss signals and return structured behavioural hints "
                "for the Goal Planner and Scheduler agents."
            ),
        },
    ],
)

# CORS (consistent with other scrum services)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all pattern observer routes under /api/pattern-observer
app.include_router(
    router,
    prefix="/api/pattern-observer",
    tags=["Pattern Analysis"],
)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root redirect to documentation."""
    return {
        "message": f"{settings.SERVICE_NAME} is running.",
        "docs": "/docs",
        "health": "/api/pattern-observer/health",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", settings.PORT))
    logger.info("[Main] Starting uvicorn on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
