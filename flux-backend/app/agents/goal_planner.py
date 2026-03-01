import json
from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import GoalPlannerOutput
from app.services.llm import check_token_budget, validated_llm_call
from app.services.supabase import db

# 9.2.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "goal_planner.txt").read_text()

_MODEL_PRIMARY = "openrouter/anthropic/claude-sonnet-4-20250514"
_MODEL_BUDGET = "openrouter/openai/gpt-4o-mini"


async def goal_planner_node(state: AgentState) -> dict:
    """
    Converts the user's goal into a concrete 6-week plan via multi-turn negotiation.

    Receives merged sub-agent outputs (classifier, scheduler, pattern_observer)
    via the reconvergence edges and builds full context before calling the LLM.
    """
    user_id: str = state["user_id"]

    # 9.2.8 — Downgrade model on hard budget limit
    budget = await check_token_budget(user_id)
    model = _MODEL_BUDGET if budget == "hard_limit" else _MODEL_PRIMARY

    # 9.2.2 — Build context from merged sub-agent outputs + profile
    profile = state.get("user_profile") or {}
    classifier_output = state.get("classifier_output") or {}
    scheduler_output = state.get("scheduler_output") or {}
    pattern_output = state.get("pattern_output") or {}
    goal_draft = state.get("goal_draft") or {}

    context_block = (
        f"\n\nContext:\n"
        f"user_profile: {json.dumps(profile)}\n"
        f"classifier_output: {json.dumps(classifier_output)}\n"
        f"scheduler_output: {json.dumps(scheduler_output)}\n"
        f"pattern_output: {json.dumps(pattern_output)}\n"
        f"goal_draft: {json.dumps(goal_draft)}\n"
    )

    # 9.2.3 — Call validated LLM with GoalPlannerOutput, max_tokens=4096
    result: GoalPlannerOutput = await validated_llm_call(
        model=model,
        system_prompt=_PROMPT + context_block,
        messages=list(state.get("conversation_history") or []),
        output_model=GoalPlannerOutput,
        max_tokens=4096,
        user_id=user_id,
    )

    # 9.2.4 — Handle multi-sprint goals that exceed 6 weeks
    if not result.goal_feasible_in_6_weeks and result.micro_goal_roadmap:
        # Write non-first micro-goals to DB as pipeline goals
        pipeline_goals = [mg for mg in result.micro_goal_roadmap if mg.pipeline_order > 1]
        for mg in pipeline_goals:
            await db.execute(
                """
                INSERT INTO goals (user_id, title, description, status, pipeline_order, target_weeks)
                VALUES ($1, $2, $3, 'pipeline', $4, $5)
                ON CONFLICT DO NOTHING
                """,
                user_id,
                mg.title,
                mg.description,
                mg.pipeline_order,
                mg.target_weeks,
            )

    # 9.2.5 — Compose assistant message with plan summary + proposed tasks
    assistant_message = result.plan_summary
    if result.proposed_tasks:
        task_lines = "\n".join(
            f"- {t.title} ({', '.join(t.scheduled_days)} at {t.suggested_time}, "
            f"{t.duration_minutes} min)"
            for t in result.proposed_tasks
        )
        assistant_message += f"\n\nProposed tasks:\n{task_lines}"

    return {
        "goal_draft": {
            **(goal_draft or {}),
            "plan": result.model_dump(),
        },
        "proposed_tasks": [t.model_dump() for t in result.proposed_tasks],
        "approval_status": result.approval_status,
        "conversation_history": list(state.get("conversation_history") or [])
        + [{"role": "assistant", "content": assistant_message}],
    }
