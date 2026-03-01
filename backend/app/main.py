"""
Flux Backend — FastAPI Application Entrypoint

Configures the FastAPI app with CORS, routers, and a health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from conv_agent import router as voice_router
from app.routers import goals, rag, scheduler

# Scrum sprint feature routers (optional — conv_agent works without them)
# Catches both ImportError (missing packages like pywebpush) and any startup
# errors such as ValueError when VAPID keys are not configured.
try:
    from scrum_40_notification_priority_model.routes import priority_router as scrum40_router
    from scrum_41_push_notification_integration.routes import router as scrum41_router
    from scrum_43_phone_call_trigger.routes import router as scrum43_router
    SCRUM_ROUTERS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Some scrum routers could not be loaded: {e}")
    SCRUM_ROUTERS_AVAILABLE = False

app = FastAPI(
    title="Flux Life Assistant API",
    description="AI-powered goal decomposition and compassionate scheduling",
    version="0.1.0",
)

# ── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────
app.include_router(goals.router)
app.include_router(rag.router)
app.include_router(scheduler.router)
app.include_router(voice_router.router)

# Include scrum sprint feature routers (if available)
if SCRUM_ROUTERS_AVAILABLE:
    app.include_router(scrum40_router)
    app.include_router(scrum41_router)
    app.include_router(scrum43_router)


# ── Health Check ────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "flux-backend"}
