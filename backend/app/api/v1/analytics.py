"""Analytics API endpoints — §17.4"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.services.supabase import db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _compute_streak(done_dates: list) -> int:
    if not done_dates:
        return 0
    unique_sorted = sorted(set(done_dates), reverse=True)
    today = date.today()
    if unique_sorted[0] < today - timedelta(days=1):
        return 0
    streak = 0
    expected = today
    for d in unique_sorted:
        if d == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif d < expected:
            break
    return streak


@router.get("/overview")
@limiter.limit("30/minute")
async def get_overview(request: Request, user=Depends(get_current_user)) -> dict:
    user_id = str(user["sub"])
    today = date.today()
    done_date_rows = await db.fetch(
        "SELECT DISTINCT DATE(scheduled_at) AS day FROM tasks WHERE user_id = $1 AND status = 'done' AND scheduled_at >= CURRENT_DATE - INTERVAL '90 days' ORDER BY day DESC",
        user_id,
    )
    streak_days = _compute_streak([row["day"] for row in done_date_rows])
    today_done = await db.fetchval("SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status = 'done' AND DATE(scheduled_at) = $2", user_id, today) or 0
    today_total = await db.fetchval("SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND status IN ('pending', 'done') AND DATE(scheduled_at) = $2", user_id, today) or 0
    today_completion_pct = (today_done / today_total) if today_total > 0 else 0.0
    heatmap_rows = await db.fetch("SELECT day, done_count FROM activity_heatmap WHERE user_id = $1 ORDER BY day DESC LIMIT 365", user_id)
    return {
        "streak_days": streak_days,
        "today_done": today_done,
        "today_total": today_total,
        "today_completion_pct": round(today_completion_pct, 4),
        "heatmap": [{"day": str(row["day"]), "done_count": row["done_count"]} for row in heatmap_rows],
    }


@router.get("/goals")
@limiter.limit("30/minute")
async def get_goals_progress(request: Request, user=Depends(get_current_user)) -> list:
    user_id = str(user["sub"])
    goals = await db.fetch("SELECT id, title, status FROM goals WHERE user_id = $1 AND status = 'active' ORDER BY pipeline_order ASC", user_id)
    result = []
    for goal in goals:
        goal_id = str(goal["id"])
        done_count = await db.fetchval("SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND goal_id = $2 AND status = 'done'", user_id, goal_id) or 0
        total_count = await db.fetchval("SELECT COUNT(*) FROM tasks WHERE user_id = $1 AND goal_id = $2 AND status IN ('pending','done')", user_id, goal_id) or 0
        result.append({"goal_id": goal_id, "title": goal["title"], "tasks_done": done_count, "tasks_total": total_count, "completion_pct": round(done_count / total_count, 4) if total_count > 0 else 0.0})
    return result


@router.get("/missed-by-cat")
@limiter.limit("30/minute")
async def get_missed_by_category(request: Request, user=Depends(get_current_user)) -> list:
    user_id = str(user["sub"])
    rows = await db.fetch("SELECT category, missed_count FROM missed_by_category WHERE user_id = $1 ORDER BY missed_count DESC", user_id)
    return [{"category": row["category"], "missed_count": row["missed_count"]} for row in rows]


@router.get("/weekly")
@limiter.limit("30/minute")
async def get_weekly_stats(request: Request, weeks: int = Query(default=12, ge=1, le=52), user=Depends(get_current_user)) -> list:
    user_id = str(user["sub"])
    rows = await db.fetch("SELECT week_start, done, total FROM user_weekly_stats WHERE user_id = $1 ORDER BY week_start DESC LIMIT $2", user_id, weeks)
    return [{"week_start": str(row["week_start"]), "done": row["done"], "total": row["total"], "completion_pct": round(row["done"] / row["total"], 4) if row["total"] > 0 else 0.0} for row in rows]
