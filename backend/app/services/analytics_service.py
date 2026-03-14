"""
Flux Backend — Analytics Service

Database operations for the analytics dashboard:
overview (streak, today stats, heatmap), weekly trends,
per-goal progress, and missed-by-category breakdown.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.database import get_supabase_client

logger = logging.getLogger(__name__)


def _db():
    """Get the Supabase client (lazy, mockable)."""
    return get_supabase_client()


# ── Overview ───────────────────────────────────────────────


def get_overview(user_id: str) -> dict[str, Any]:
    """
    Build the analytics overview:
    - streak_days via RPC calculate_streak
    - today_done / today_total from tasks table
    - heatmap via RPC daily_heatmap
    """
    # 1. Streak
    streak_result = (
        _db()
        .rpc(
            "calculate_streak",
            {"p_user_id": user_id},
        )
        .execute()
    )
    streak_days = streak_result.data if isinstance(streak_result.data, int) else 0

    # 2. Today's tasks
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    day_end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

    today_result = (
        _db()
        .table("tasks")
        .select("id, status")
        .eq("user_id", user_id)
        .gte("scheduled_at", day_start)
        .lte("scheduled_at", day_end)
        .execute()
    )
    today_tasks = today_result.data or []
    today_total = len(today_tasks)
    today_done = sum(1 for t in today_tasks if t.get("status") == "done")
    today_completion_pct = (
        round(today_done / today_total, 4) if today_total > 0 else None
    )

    # 3. Heatmap
    heatmap_result = (
        _db()
        .rpc(
            "daily_heatmap",
            {"p_user_id": user_id, "p_days": 365},
        )
        .execute()
    )
    heatmap = heatmap_result.data or []

    return {
        "streak_days": streak_days,
        "today_done": today_done,
        "today_total": today_total,
        "today_completion_pct": today_completion_pct,
        "heatmap": heatmap,
    }


# ── Weekly Stats ───────────────────────────────────────────


def get_weekly(user_id: str, weeks: int = 12) -> list[dict[str, Any]]:
    """
    Query user_weekly_stats materialized view, return last N weeks.
    Converts completion_pct from 0–100 to 0.0–1.0.
    """
    result = (
        _db()
        .table("user_weekly_stats")
        .select("week, completed, total, completion_pct")
        .eq("user_id", user_id)
        .order("week", desc=True)
        .limit(weeks)
        .execute()
    )

    rows = result.data or []
    return [
        {
            "week_start": (
                row["week"][:10]
                if isinstance(row["week"], str)
                else str(row["week"])[:10]
            ),
            "done": row["completed"],
            "total": row["total"],
            "completion_pct": round(float(row["completion_pct"]) / 100, 4),
        }
        for row in rows
    ]


# ── Goals Progress ─────────────────────────────────────────


def get_goals(user_id: str) -> list[dict[str, Any]]:
    """
    For each active goal, count done vs total tasks.
    """
    goals_result = (
        _db()
        .table("goals")
        .select("id, title")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )
    goals = goals_result.data or []
    if not goals:
        return []

    goal_ids = [g["id"] for g in goals]

    tasks_result = (
        _db()
        .table("tasks")
        .select("goal_id, status")
        .eq("user_id", user_id)
        .in_("goal_id", goal_ids)
        .execute()
    )
    tasks = tasks_result.data or []

    # Aggregate per goal
    stats: dict[str, dict[str, int]] = {
        gid: {"done": 0, "total": 0} for gid in goal_ids
    }
    for t in tasks:
        gid = t.get("goal_id")
        if gid and gid in stats:
            stats[gid]["total"] += 1
            if t.get("status") == "done":
                stats[gid]["done"] += 1

    return [
        {
            "goal_id": g["id"],
            "title": g["title"],
            "tasks_done": stats[g["id"]]["done"],
            "tasks_total": stats[g["id"]]["total"],
            "completion_pct": (
                round(stats[g["id"]]["done"] / stats[g["id"]]["total"], 4)
                if stats[g["id"]]["total"] > 0
                else 0.0
            ),
        }
        for g in goals
    ]


# ── Missed by Category ────────────────────────────────────


def get_missed_by_category(user_id: str) -> list[dict[str, Any]]:
    """
    Query missed_by_category materialized view.
    The view stores class_tags as raw TEXT[] — we unnest in Python
    and accumulate missed_count per individual tag.
    """
    result = (
        _db()
        .table("missed_by_category")
        .select("class_tags, missed_count")
        .eq("user_id", user_id)
        .execute()
    )
    rows = result.data or []

    category_totals: dict[str, int] = {}
    for row in rows:
        tags = row.get("class_tags")
        missed = row.get("missed_count", 0)
        if not tags:
            continue
        if isinstance(tags, list):
            for tag in tags:
                category_totals[tag] = category_totals.get(tag, 0) + missed
        elif isinstance(tags, str):
            category_totals[tags] = category_totals.get(tags, 0) + missed

    return [
        {"category": cat, "missed_count": count}
        for cat, count in sorted(category_totals.items(), key=lambda x: -x[1])
    ]
