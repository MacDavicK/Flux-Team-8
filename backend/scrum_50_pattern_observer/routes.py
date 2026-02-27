"""FastAPI routes for the Pattern Observer service (SCRUM-50).

Swagger / OpenAPI annotations are provided on every endpoint via
`response_model`, `summary`, `description`, and `responses` kwargs.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from config import settings
from logger import get_logger
from models import (
    ConsultationRequest,
    ConsultationResponse,
    HealthResponse,
    MissSignalResponse,
    TaskMissSignal,
)
from pattern_service import PatternService

logger = get_logger("pattern_observer.routes")

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: shared PatternService instance
# ---------------------------------------------------------------------------

_service: PatternService | None = None


def get_service() -> PatternService:
    """Return the module-level PatternService singleton."""
    global _service
    if _service is None:
        _service = PatternService()
        logger.debug("[Routes] PatternService singleton created")
    return _service


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the running status of the Pattern Observer service.",
    tags=["Health"],
)
async def health() -> HealthResponse:
    logger.debug("[Routes] Health check requested")
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
    )


# ---------------------------------------------------------------------------
# Consultation
# ---------------------------------------------------------------------------

@router.post(
    "/consult",
    response_model=ConsultationResponse,
    status_code=status.HTTP_200_OK,
    summary="Consult pattern observer",
    description=(
        "Called by the Goal Planner or Scheduler agent to retrieve structured "
        "behavioural hints for a specific user. "
        "Returns best scheduling times, avoidance slots, and per-category completion rates. "
        "New users receive cold-start defaults until sufficient history is collected."
    ),
    responses={
        200: {"description": "Pattern summary returned successfully"},
        500: {"description": "Internal error during LLM analysis or DAO fetch"},
    },
    tags=["Pattern Analysis"],
)
async def consult(
    request: ConsultationRequest,
    service: PatternService = Depends(get_service),
) -> ConsultationResponse:
    logger.info(
        "[Routes] POST /consult | user=%s", request.user_id
    )
    try:
        return await service.consult(request)
    except Exception as exc:
        logger.error(
            "[Routes] /consult failed | user=%s | error=%s",
            request.user_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pattern analysis failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Task-miss signal
# ---------------------------------------------------------------------------

@router.post(
    "/miss-signal",
    response_model=MissSignalResponse,
    status_code=status.HTTP_200_OK,
    summary="Report a missed task",
    description=(
        "Emitted by the Notifier Agent or Scheduler when a task is marked as missed. "
        "The Pattern Observer checks whether the same time-slot (same day of week, "
        "\u00b1SLOT_TOLERANCE_HOURS) has been missed \u2265 3 times across 3 consecutive weeks. "
        "If so, an avoidance-pattern record is written to the DAO service."
    ),
    responses={
        200: {"description": "Miss signal processed; avoidance_flagged indicates whether a pattern was recorded"},
        422: {"description": "Validation error in request body"},
        500: {"description": "Internal error during avoidance detection"},
    },
    tags=["Pattern Analysis"],
)
async def miss_signal(
    signal: TaskMissSignal,
    service: PatternService = Depends(get_service),
) -> MissSignalResponse:
    logger.info(
        "[Routes] POST /miss-signal | user=%s | task=%s",
        signal.user_id,
        signal.task_id,
    )
    try:
        return await service.handle_miss_signal(signal)
    except Exception as exc:
        logger.error(
            "[Routes] /miss-signal failed | user=%s | error=%s",
            signal.user_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Miss signal processing failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Pattern history (read-only, for debugging / admin)
# ---------------------------------------------------------------------------

@router.get(
    "/patterns/{user_id}",
    summary="Get user patterns",
    description=(
        "Retrieve all pattern records stored in the DAO service for a given user. "
        "Intended for debugging and admin review."
    ),
    responses={
        200: {"description": "List of Pattern records"},
        502: {"description": "DAO service unreachable"},
    },
    tags=["Pattern Analysis"],
)
async def get_patterns(
    user_id: UUID,
    service: PatternService = Depends(get_service),
) -> JSONResponse:
    logger.info("[Routes] GET /patterns/%s", user_id)
    import httpx

    try:
        resp = await service._client().get("/patterns", params={"user_id": str(user_id)})
        resp.raise_for_status()
        return JSONResponse(content=resp.json())
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[Routes] DAO patterns fetch failed | status=%d",
            exc.response.status_code,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="DAO service returned an error while fetching patterns.",
        )
    except Exception as exc:
        logger.error(
            "[Routes] /patterns/%s failed | error=%s", user_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
