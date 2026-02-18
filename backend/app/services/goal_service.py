"""
Flux Backend — Goal Service

Database operations for goals, milestones, tasks, and conversations.
All writes go through Supabase's Python client.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from app.database import get_supabase_client
from app.models.schemas import PlanMilestone

logger = logging.getLogger(__name__)


def _db():
    """Get the Supabase client (lazy, mockable)."""
    return get_supabase_client()


# ── Conversations ───────────────────────────────────────────

def create_conversation(user_id: str, initial_state: dict) -> str:
    """
    Insert a new conversation row.
    Returns the conversation ID (UUID).
    """
    result = (
        _db().table("conversations")
        .insert({
            "user_id": user_id,
            "goal_id": None,  # goal_id will be set later when the goal is created
            "messages": json.dumps(initial_state.get("messages", [])),
            "status": "open",
        })
        .execute()
    )
    return result.data[0]["id"]


def get_conversation(conversation_id: str) -> Optional[dict]:
    """Fetch a conversation row by ID."""
    result = (
        _db().table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .single()
        .execute()
    )
    return result.data


def update_conversation(conversation_id: str, agent_state: dict) -> None:
    """Persist the full agent state into the conversation's messages JSONB."""
    _db().table("conversations").update({
        "messages": json.dumps(agent_state),
        "status": agent_state.get("state", "open"),
    }).eq("id", conversation_id).execute()


def link_conversation_to_goal(conversation_id: str, goal_id: str) -> None:
    """Set the goal_id on the conversation once the goal is created."""
    _db().table("conversations").update({
        "goal_id": goal_id,
    }).eq("id", conversation_id).execute()


# ── Goals ───────────────────────────────────────────────────

def create_goal(user_id: str, title: str, category: str = "health_fitness", timeline: str = None) -> str:
    """
    Insert a new goal row.
    Returns the goal ID (UUID).
    """
    result = (
        _db().table("goals")
        .insert({
            "user_id": user_id,
            "title": title,
            "category": category,
            "timeline": timeline,
            "status": "active",
        })
        .execute()
    )
    return result.data[0]["id"]


# ── Milestones ──────────────────────────────────────────────

def create_milestones(goal_id: str, milestones: list[PlanMilestone]) -> list[str]:
    """
    Batch-insert milestone rows for a goal.
    Returns list of milestone IDs.
    """
    rows = [
        {
            "goal_id": goal_id,
            "week_number": m.week,
            "title": m.title,
            "status": "pending",
        }
        for m in milestones
    ]
    result = _db().table("milestones").insert(rows).execute()
    return [row["id"] for row in result.data]


# ── Tasks ───────────────────────────────────────────────────

def create_tasks_from_plan(
    user_id: str,
    goal_id: str,
    milestones: list[PlanMilestone],
    milestone_ids: list[str],
    start_date: Optional[datetime] = None,
) -> list[str]:
    """
    Create recurring task rows from the generated plan.

    For each milestone (week), creates tasks spread across the week.
    Returns list of task IDs.
    """
    if start_date is None:
        start_date = datetime.utcnow()

    task_rows = []
    for i, milestone in enumerate(milestones):
        milestone_id = milestone_ids[i] if i < len(milestone_ids) else None
        week_start = start_date + timedelta(weeks=i)

        for j, task_title in enumerate(milestone.tasks):
            # Spread tasks across the week (Mon-Fri roughly)
            task_day = week_start + timedelta(days=j % 5)
            task_start = task_day.replace(hour=9, minute=0, second=0, microsecond=0)
            task_end = task_start + timedelta(hours=1)

            task_rows.append({
                "user_id": user_id,
                "goal_id": goal_id,
                "milestone_id": milestone_id,
                "title": task_title,
                "start_time": task_start.isoformat(),
                "end_time": task_end.isoformat(),
                "state": "scheduled",
                "priority": "standard",
                "trigger_type": "time",
                "is_recurring": True,
            })

    if not task_rows:
        return []

    result = _db().table("tasks").insert(task_rows).execute()
    return [row["id"] for row in result.data]


# ── Full Plan Persistence ──────────────────────────────────

def save_complete_plan(
    user_id: str,
    conversation_id: str,
    agent_context: dict,
    milestones: list[PlanMilestone],
) -> dict:
    """
    Save the entire plan to the database:
    1. Create the Goal
    2. Create Milestones
    3. Create Tasks
    4. Link conversation to goal

    Returns a summary dict with all created IDs.
    """
    goal_title = agent_context.get("goal", "Health & Fitness Goal")
    timeline = agent_context.get("timeline", None)

    # 1. Create goal
    goal_id = create_goal(
        user_id=user_id,
        title=goal_title,
        category="health_fitness",
        timeline=timeline,
    )

    # 2. Create milestones
    milestone_ids = create_milestones(goal_id, milestones)

    # 3. Create tasks
    task_ids = create_tasks_from_plan(
        user_id=user_id,
        goal_id=goal_id,
        milestones=milestones,
        milestone_ids=milestone_ids,
    )

    # 4. Link conversation
    link_conversation_to_goal(conversation_id, goal_id)

    logger.info(
        f"Plan saved: goal={goal_id}, "
        f"milestones={len(milestone_ids)}, tasks={len(task_ids)}"
    )

    return {
        "goal_id": goal_id,
        "milestone_ids": milestone_ids,
        "task_ids": task_ids,
    }
