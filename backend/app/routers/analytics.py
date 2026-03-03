"""
Flux Backend — Analytics Router

REST endpoints for the analytics dashboard.
All endpoints require JWT authentication via Supabase.

Prefix: /api/v1/analytics
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.models.schemas import (
    AnalyticsGoalItem,
    AnalyticsMissedByCategoryItem,
    AnalyticsOverviewResponse,
    AnalyticsWeeklyItem,
)
from app.services import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


# ── GET /api/v1/analytics/overview ─────────────────────────
@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def analytics_overview(user: dict = Depends(get_current_user)):
    """
    Return analytics overview: streak, today's stats, and activity heatmap.
    """
    user_id = user["sub"]
    try:
        data = analytics_service.get_overview(user_id)
        return AnalyticsOverviewResponse(**data)
    except Exception as e:
        logger.error("Analytics overview failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load analytics overview")


# ── GET /api/v1/analytics/weekly ───────────────────────────
@router.get("/weekly", response_model=list[AnalyticsWeeklyItem])
async def analytics_weekly(
    weeks: int = Query(default=12, ge=1, le=52, description="Number of weeks"),
    user: dict = Depends(get_current_user),
):
    """
    Return weekly completion stats for the last N weeks.
    """
    user_id = user["sub"]
    try:
        rows = analytics_service.get_weekly(user_id, weeks)
        return [AnalyticsWeeklyItem(**row) for row in rows]
    except Exception as e:
        logger.error("Analytics weekly failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load weekly analytics")


# ── GET /api/v1/analytics/goals ────────────────────────────
@router.get("/goals", response_model=list[AnalyticsGoalItem])
async def analytics_goals(user: dict = Depends(get_current_user)):
    """
    Return per-goal progress (tasks done vs total) for active goals.
    """
    user_id = user["sub"]
    try:
        rows = analytics_service.get_goals(user_id)
        return [AnalyticsGoalItem(**row) for row in rows]
    except Exception as e:
        logger.error("Analytics goals failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load goal analytics")


# ── GET /api/v1/analytics/missed-by-cat ────────────────────
@router.get("/missed-by-category", response_model=list[AnalyticsMissedByCategoryItem])
async def analytics_missed_by_category(user: dict = Depends(get_current_user)):
    """
    Return missed task counts grouped by goal category tag.
    """
    user_id = user["sub"]
    try:
        rows = analytics_service.get_missed_by_category(user_id)
        return [AnalyticsMissedByCategoryItem(**row) for row in rows]
    except Exception as e:
        logger.error("Analytics missed-by-cat failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to load missed-by-category analytics",
        )
