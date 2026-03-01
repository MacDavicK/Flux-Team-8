import json
from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import PatternObserverOutput
from app.services.llm import validated_llm_call
from app.services.supabase import db
from app.config import settings

# 9.5.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "pattern_observer.txt").read_text()

_MODEL = "openrouter/openai/gpt-4o-mini"


async def pattern_observer_node(state: AgentState) -> dict:
    """
    Analyzes task completion/miss history and returns scheduling recommendations.
    """
    user_id: str = state["user_id"]
    profile: dict = state.get("user_profile") or {}

    # 9.5.2 — Query task history (completions + misses with timestamps)
    history = await db.fetch(
        """
        SELECT title, status, scheduled_at, completed_at, duration_minutes,
               COALESCE(class_tags, ARRAY[]::text[]) AS class_tags
        FROM tasks
        WHERE user_id = $1
          AND status IN ('done', 'missed')
        ORDER BY scheduled_at DESC
        LIMIT 200
        """,
        user_id,
    )
    history_data = [
        {
            "title": row["title"],
            "status": row["status"],
            "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            "duration_minutes": row["duration_minutes"],
            "tags": list(row["class_tags"]),
        }
        for row in history
    ]

    # 9.5.6 — Cold-start: fewer than 14 days of data → use chronotype as baseline
    chronotype = profile.get("chronotype", "morning")
    cold_start_note = ""
    if len(history_data) == 0:
        cold_start_note = (
            f"\nCold-start user: no history available. "
            f"Use chronotype='{chronotype}' as baseline. "
            f"Set confidence < 0.5 on all patterns."
        )

    context_block = (
        f"\n\nContext:\n"
        f"task_history: {json.dumps(history_data)}\n"
        f"user_profile: {json.dumps(profile)}\n"
        f"{cold_start_note}"
    )

    # 9.5.3 — Call validated LLM with PatternObserverOutput, max_tokens=1024
    result: PatternObserverOutput = await validated_llm_call(
        model=_MODEL,
        system_prompt=_PROMPT + context_block,
        messages=[{"role": "user", "content": "Analyze this user's scheduling patterns."}],
        output_model=PatternObserverOutput,
        max_tokens=1024,
        user_id=user_id,
    )

    return {
        "pattern_output": {
            "best_times": result.best_times,
            "avoid_slots": [s.model_dump() for s in result.avoid_slots],
            "category_performance": [p.model_dump() for p in result.category_performance],
            "general_notes": result.general_notes,
        }
    }


async def check_and_flag_pattern(user_id: str, task_id: str) -> None:
    """
    9.5.4 — Miss signal handler: called by Notifier when a task is marked missed.
    Checks for ≥3 consecutive misses in the same slot (±1 hour, same day of week,
    3 consecutive weeks). Creates/updates a patterns row if threshold met.
    9.5.5 — Skips overwrite if patterns.data.user_overridden = true.
    """
    # Find the missed task
    task = await db.fetchrow(
        "SELECT title, scheduled_at, class_tags FROM tasks WHERE id = $1 AND user_id = $2",
        task_id,
        user_id,
    )
    if not task or not task["scheduled_at"]:
        return

    scheduled_at = task["scheduled_at"]
    day_of_week = scheduled_at.strftime("%A")

    # Count consecutive misses in same slot (±1 hour, same day, last 3 weeks)
    miss_count = await db.fetchval(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = $1
          AND status = 'missed'
          AND EXTRACT(DOW FROM scheduled_at) = EXTRACT(DOW FROM $2::timestamptz)
          AND ABS(EXTRACT(EPOCH FROM (scheduled_at::time - $2::timestamptz::time))) <= 3600
          AND scheduled_at >= $2::timestamptz - INTERVAL '3 weeks'
        """,
        user_id,
        scheduled_at,
    )

    if (miss_count or 0) < settings.pattern_miss_threshold:
        return

    # Build pattern data
    time_str = scheduled_at.strftime("%H:%M")
    pattern_key = f"{day_of_week}_{time_str}"
    confidence = min(0.95, 0.6 + (miss_count - 3) * 0.05)

    # 9.5.5 — Do not overwrite user-overridden patterns
    existing = await db.fetchrow(
        """
        SELECT id, data FROM patterns
        WHERE user_id = $1 AND pattern_type = 'time_avoidance' AND pattern_key = $2
        """,
        user_id,
        pattern_key,
    )
    if existing and (existing["data"] or {}).get("user_overridden"):
        return

    if existing:
        await db.execute(
            """
            UPDATE patterns
            SET confidence = $1, updated_at = now(),
                data = data || jsonb_build_object('miss_count', $2)
            WHERE id = $3
            """,
            confidence,
            miss_count,
            existing["id"],
        )
    else:
        await db.execute(
            """
            INSERT INTO patterns (user_id, pattern_type, pattern_key, description, confidence, data)
            VALUES ($1, 'time_avoidance', $2, $3, $4, $5::jsonb)
            """,
            user_id,
            pattern_key,
            f"Consistently missed on {day_of_week} around {time_str}",
            confidence,
            json.dumps({"miss_count": miss_count, "day": day_of_week, "time": time_str}),
        )
