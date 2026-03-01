"""
Flux API — FastAPI application entry point. Tasks 18.1–18.7.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from slowapi.errors import RateLimitExceeded

from app.config import settings

# ── 18.1  Sentry — before FastAPI instance ────────────────────────────────────
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration(), AsyncioIntegration()],
    traces_sample_rate=settings.sentry_traces_sample_rate,
    environment=settings.sentry_environment,
    send_default_pii=False,
)

from app.middleware.logging import StructlogMiddleware  # noqa: E402
from app.middleware.rate_limit import limiter  # noqa: E402
from app.services.supabase import close_pool, init_pool  # noqa: E402

from app.api.v1.account import router as account_router  # noqa: E402
from app.api.v1.analytics import router as analytics_router  # noqa: E402
from app.api.v1.chat import router as chat_router  # noqa: E402
from app.api.v1.demo import router as demo_router  # noqa: E402
from app.api.v1.echoconfig import router as echoconfig_router  # noqa: E402
from app.api.v1.goals import router as goals_router  # noqa: E402
from app.api.v1.patterns import router as patterns_router  # noqa: E402
from app.api.v1.tasks import router as tasks_router  # noqa: E402
from app.api.v1.webhooks import router as webhooks_router  # noqa: E402


async def _rate_limit_handler(request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)


# ── 18.7  Lifespan ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()

    from app.agents.graph import _build_graph, checkpointer_lifespan
    import app.agents.graph as graph_module

    async with checkpointer_lifespan() as cp:
        graph_module.compiled_graph = _build_graph().compile(checkpointer=cp)
        yield

    await close_pool()


# ── 18.2  FastAPI app ─────────────────────────────────────────────────────────

app = FastAPI(
    title="Flux API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── 18.3  Rate limiter ────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# ── 18.4  Middleware ──────────────────────────────────────────────────────────

app.add_middleware(StructlogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 18.5  Routers ─────────────────────────────────────────────────────────────

_PREFIX = "/api/v1"
app.include_router(chat_router,      prefix=_PREFIX)
app.include_router(goals_router,     prefix=_PREFIX)
app.include_router(tasks_router,     prefix=_PREFIX)
app.include_router(analytics_router, prefix=_PREFIX)
app.include_router(patterns_router,  prefix=_PREFIX)
app.include_router(account_router,   prefix=_PREFIX)
app.include_router(webhooks_router,  prefix=_PREFIX)
app.include_router(demo_router,      prefix=_PREFIX)
app.include_router(echoconfig_router)


# ── 18.6  Custom OpenAPI with BearerAuth ──────────────────────────────────────

def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description="Flux — AI-powered goal and task management API",
        routes=app.routes,
    )

    schema.setdefault("components", {})
    schema["components"].setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Supabase JWT. Pass as: Authorization: Bearer <token>",
    }

    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]
