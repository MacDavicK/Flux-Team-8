"""Main entry point for the Notifier Agent (SCRUM-57).

Combines a FastAPI web server (for webhooks/status) with the
background escalation scheduler (APScheduler).
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the backend root is in the path for dao_service imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dao_service.core.database import DatabaseSession
from dao_service.services.dao_task_service import DaoTaskService

from .routes import router
from .scheduler import start_scheduler, stop_scheduler

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifecycle Management (Lifespan)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise services and start the background scheduler on startup."""
    logger.info("--- Starting Notifier Agent ---")
    
    # 1. Initialise core dependencies
    task_service = DaoTaskService()
    db = DatabaseSession()
    
    # 2. Start the background escalation ladder
    start_scheduler(task_service, db)
    
    yield
    
    # 3. Graceful shutdown
    logger.info("--- Shutting down Notifier Agent ---")
    stop_scheduler()


# ---------------------------------------------------------------------------
# FastAPI Application setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Notifier Agent API",
    description="Background service for task monitoring and multi-channel escalation (SCRUM-57).",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend/integration access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the agent's internal routes (webhooks, health, etc.)
app.include_router(router)


@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    """Root redirect to documentation."""
    return {
        "message": "Notifier Agent is running.",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8057"))
    logger.info("Starting uvicorn on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
