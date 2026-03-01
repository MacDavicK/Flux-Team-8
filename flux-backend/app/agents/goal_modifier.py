"""
11.3 — goal_modifier node (§11).

Handles the MODIFY_GOAL intent:
  1. Finds the goal to modify (goal_id from goal_draft or conversation context).
  2. Cancels all future pending tasks for that goal that are not shared with
     another active goal (shared_with_goal_ids check).
  3. Uses the LLM to generate a revised set of proposed tasks based on the
     user's modification request and the original plan.
  4. Returns proposed_tasks for save_tasks to insert, and presents a summary.

The graph edge is goal_modifier → save_tasks → END (no negotiation loop),
so the LLM reply acts as the confirmation to the user.
"""

from __future__ import annotations

import json

import pendulum

from app.agents.state import AgentState
from app.models.agent_outputs import GoalPlannerOutput
from app.services.llm import check_token_budget, validated_llm_call
from app.services.supabase import db

_MODEL_PRIMARY = "openrouter/anthropic/claude-sonnet-4-20250514"
_MODEL_BUDGET = "openrouter/openai/gpt-4o-mini"

_SYSTEM = """\
You are a personal coach helping a user modify an existing goal plan in Flux.

The user has an active goal with existing tasks. They want to change something
(frequency, timing, difficulty, specific days, etc.).

You will receive:
- original_plan: the previously negotiated plan JSON
- cancelled_tasks: list of future task titles that were just cancelled
- user_profile: schedule, sleep window, work hours, chronotype
- modification_request: the user's latest message describing what they want changed

Your job:
1. Understand what the user wants to change.
2. Generate a REVISED set of proposed_tasks that replaces the cancelled ones.
3. Keep unchanged tasks as-is — only regenerate tasks affected by the modification.
4. Respect the user's schedule constraints (sleep_window, work_hours, pattern_output).
5. Present a clear summary of what changed.

Set approval_status to "approved" — the user has already requested the change,
so write it immediately without asking again.

Output ONLY valid JSON matching this schema (no markdown fences):
{
  "goal_feasible_in_6_weeks": true,
  "micro_goal_roadmap": null,
  "proposed_tasks": [
    {
      "title": "",
      "description": "",
      "scheduled_days": ["Monday"],
      "suggested_time": "07:00",
      "duration_minutes": 30,
      "recurrence_rule": "FREQ=WEEKLY;BYDAY=MO",
      "week_range": [1, 6]
    }
  ],
  "conflicts_detected": [],
  "plan_summary": "Human-readable summary of what changed",
  "approval_status": "approved"
}

All times in suggested_time must be in the user's LOCAL timezone."""


async def goal_modifier_node(state: AgentState) -> dict:
    """
    11.3 — Handles MODIFY_GOAL intent.

    Cancels affected future tasks, regenerates the plan via LLM, and returns
    proposed_tasks for save_tasks to insert.
    """
    user_id: str = state["user_id"]
    profile: dict = state.get("user_profile") or {}
    history: list[dict] = list(state.get("conversation_history") or [])
    goal_draft: dict = state.get("goal_draft") or {}
    user_tz: str = profile.get("timezone", "UTC")

    # ── Step 1: Resolve goal_id ───────────────────────────────────────────
    goal_id: str | None = goal_draft.get("goal_id")

    if not goal_id:
        # Try to find the user's most recently active goal as fallback
        row = await db.fetchrow(
            """
            SELECT id FROM goals
            WHERE user_id = $1 AND status = 'active'
            ORDER BY activated_at DESC NULLS LAST
            LIMIT 1
            """,
            user_id,
        )
        if row:
            goal_id = str(row["id"])

    if not goal_id:
        fallback = (
            "I couldn't find an active goal to modify. "
            "Could you tell me which goal you'd like to change?"
        )
        return {
            "conversation_history": history + [
                {"role": "assistant", "content": fallback}
            ],
        }

    # ── Step 2: Fetch goal details ────────────────────────────────────────
    goal_row = await db.fetchrow(
        "SELECT title, description, plan_json FROM goals WHERE id = $1 AND user_id = $2",
        goal_id,
        user_id,
    )
    original_plan: dict = {}
    if goal_row and goal_row["plan_json"]:
        try:
            original_plan = (
                json.loads(goal_row["plan_json"])
                if isinstance(goal_row["plan_json"], str)
                else goal_row["plan_json"]
            )
        except Exception:
            original_plan = {}

    # ── Step 3: Cancel future pending tasks not shared with another goal ──
    now_utc = pendulum.now("UTC")
    future_tasks = await db.fetch(
        """
        SELECT id, title, shared_with_goal_ids
        FROM tasks
        WHERE goal_id = $1
          AND user_id  = $2
          AND status   = 'pending'
          AND (scheduled_at IS NULL OR scheduled_at >= $3)
        """,
        goal_id,
        user_id,
        now_utc,
    )

    cancelled_titles: list[str] = []
    for task in future_tasks:
        shared_ids: list = list(task["shared_with_goal_ids"] or [])
        # Check if any sibling goal_id in shared_with_goal_ids is still active
        if shared_ids:
            active_sibling = await db.fetchval(
                """
                SELECT id FROM goals
                WHERE id = ANY($1::uuid[]) AND status = 'active' AND id != $2
                LIMIT 1
                """,
                shared_ids,
                goal_id,
            )
            if active_sibling:
                # Keep this task — it's shared with another live goal
                continue

        await db.execute(
            "UPDATE tasks SET status = 'cancelled' WHERE id = $1",
            task["id"],
        )
        cancelled_titles.append(task["title"])

    # ── Step 4: Build LLM context ─────────────────────────────────────────
    budget = await check_token_budget(user_id)
    model = _MODEL_BUDGET if budget == "hard_limit" else _MODEL_PRIMARY

    context_block = (
        f"\n\nContext:\n"
        f"goal_id: {goal_id}\n"
        f"original_plan: {json.dumps(original_plan)}\n"
        f"cancelled_tasks: {json.dumps(cancelled_titles)}\n"
        f"user_profile: {json.dumps(profile)}\n"
        f"user_timezone: {user_tz}\n"
    )

    # ── Step 5: Generate revised plan via LLM ────────────────────────────
    try:
        result: GoalPlannerOutput = await validated_llm_call(
            model=model,
            system_prompt=_SYSTEM + context_block,
            messages=history,
            output_model=GoalPlannerOutput,
            max_tokens=2048,
            user_id=user_id,
        )
    except ValueError:
        fallback = (
            "Sorry, I had trouble generating the revised plan. "
            "Could you describe the change you'd like more specifically?"
        )
        return {
            "conversation_history": history + [
                {"role": "assistant", "content": fallback}
            ],
        }

    # ── Step 6: Compose proposed_tasks with goal context ─────────────────
    proposed = [
        {**t.model_dump(), "goal_id": goal_id, "shared_with_goal_ids": []}
        for t in result.proposed_tasks
    ]

    # ── Step 7: Update the goal's plan_json snapshot ─────────────────────
    await db.execute(
        "UPDATE goals SET plan_json = $1::jsonb WHERE id = $2",
        json.dumps(result.model_dump()),
        goal_id,
    )

    return {
        "proposed_tasks": proposed,
        "approval_status": "approved",
        "goal_draft": {**goal_draft, "goal_id": goal_id, "plan": result.model_dump()},
        "conversation_history": history + [
            {"role": "assistant", "content": result.plan_summary}
        ],
    }
