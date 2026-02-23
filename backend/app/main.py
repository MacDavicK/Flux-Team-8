"""
Flux Backend — FastAPI Application Entrypoint

Configures the FastAPI app with CORS, routers, and a health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import goals, rag, scheduler

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


# ── Health Check ────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "flux-backend"}
