import json
from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import GoalPlannerOutput, UserPreferenceExtractOutput
from app.services.llm import check_token_budget, validated_llm_call
from app.services.supabase import db
from app.services.user_notes import get_user_notes, upsert_user_note

# conversation_id is threaded through goal_draft so we can update the title
_CONV_ID_KEY = "_conversation_id"

# 9.2.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "goal_planner.txt").read_text()

_MODEL_PRIMARY = "openrouter/anthropic/claude-sonnet-4"
_MODEL_BUDGET = "openrouter/openai/gpt-4o-mini"

# Lightweight prompt to extract explicit user habit/constraint statements from conversation.
_PREFERENCE_EXTRACT_PROMPT = """\
You are a context extractor. Given a conversation, identify any explicit user statements
about EXISTING habits, routines, or constraints that should be remembered for future planning.

IMPORTANT DISTINCTION:
- EXTRACT: things the user currently does or is constrained by (present tense, ongoing reality)
- DO NOT EXTRACT: goals, aspirations, or things the user *wants* to start doing

Examples of things to EXTRACT:
- "I go to the gym on Tuesday evenings" → already doing this, extract it
- "I already run in the mornings" → already doing this, extract it
- "I can't do anything before 9 AM because of the school run" → existing constraint, extract it
- "I work nights so mornings are bad for me" → existing constraint, extract it

Examples of things to NOT EXTRACT (these are goals, not existing habits):
- "I want to learn Japanese" → goal/aspiration, NOT an existing habit
- "I want to start running" → goal, NOT an existing habit
- "I'd like to learn German" → goal, NOT an existing habit
- "I want to lose weight" → goal, NOT an existing habit

Rules:
- Only extract things the user explicitly stated as CURRENT/EXISTING in THIS conversation turn.
- Do NOT extract goals, aspirations, or things the user wants to start.
- Do NOT infer or guess — only extract clear, direct statements about existing reality.
- If nothing qualifying was stated, return an empty notes list.
- Generate a stable slug key: lowercase, underscores, e.g. "gym_tuesday_evening".

Output ONLY valid JSON matching this schema:
{
  "notes": [
    {
      "key": "gym_tuesday_evening",
      "description": "Goes to gym on Tuesday evenings around 19:00",
      "activity": "gym",
      "days": ["Tuesday"],
      "time": "19:00",
      "duration_minutes": 60
    }
  ]
}
"""


async def goal_planner_node(state: AgentState) -> dict:
    """
    Converts the user's goal into a concrete 6-week plan via multi-turn negotiation.

    Handles two entry paths:
    - GOAL intent (new goal): builds the full roadmap; proposed_tasks always covers
      the first milestone (pipeline_order=1) so the UI can show tasks immediately.
    - NEXT_MILESTONE intent: loads the target pipeline goal from DB, marks the
      previously active goal as completed, activates the pipeline goal, and plans
      proposed_tasks specifically for it.

    Called twice per goal turn (fan-out pattern):
    1. Before sub-agents: sub-agent outputs are None → return empty dict so
       route_from_goal_planner can dispatch the Send() fan-out.
    2. After sub-agents converge: all outputs present → run the full LLM call.
    """
    user_id: str = state["user_id"]

    # 9.2.2 — Only generate the plan once all sub-agent outputs are available.
    # On the first call they are None (fan-out not yet triggered); return early
    # so route_from_goal_planner can dispatch the Send() fan-out.
    classifier_done = state.get("classifier_output") is not None
    scheduler_done = state.get("scheduler_output") is not None
    pattern_done = state.get("pattern_output") is not None

    if not (classifier_done and scheduler_done and pattern_done):
        # Sub-agents haven't run yet — nothing to do here; routing will fan out.
        return {}

    # 9.2.8 — Downgrade model on hard budget limit
    budget = await check_token_budget(user_id)
    model = _MODEL_BUDGET if budget == "hard_limit" else _MODEL_PRIMARY

    profile = state.get("user_profile") or {}
    classifier_output = state.get("classifier_output") or {}
    scheduler_output = state.get("scheduler_output") or {}
    pattern_output = state.get("pattern_output") or {}
    goal_draft = state.get("goal_draft") or {}
    intent = state.get("intent") or "GOAL"

    # Load stored user preference notes (habits / constraints from past conversations)
    user_notes = await get_user_notes(user_id)

    # ── NEXT_MILESTONE: resolve target pipeline goal, transition statuses ─────
    milestone_context_block = ""
    next_goal_id: str | None = None

    if intent == "NEXT_MILESTONE":
        # milestone_order may come from orchestrator state or goal_draft
        _draft: dict = goal_draft  # plain dict — avoid TypedDict narrowing issues
        milestone_order: int | None = state.get("milestone_order") or _draft.get("milestone_order")
        parent_goal_id: str | None = _draft.get("goal_id")

        # If no explicit order, resolve: find the lowest pipeline_order still pending
        if milestone_order is None:
            row = await db.fetchrow(
                """
                SELECT pipeline_order FROM goals
                WHERE user_id = $1
                  AND status = 'pipeline'
                ORDER BY pipeline_order ASC
                LIMIT 1
                """,
                user_id,
            )
            if row:
                milestone_order = row["pipeline_order"]

        # Fetch the target pipeline goal
        if milestone_order is not None:
            pipeline_row = await db.fetchrow(
                """
                SELECT id, title, description, pipeline_order, target_weeks
                FROM goals
                WHERE user_id = $1 AND pipeline_order = $2 AND status = 'pipeline'
                LIMIT 1
                """,
                user_id,
                milestone_order,
            )
            if pipeline_row:
                next_goal_id = str(pipeline_row["id"])
                milestone_context_block = (
                    f"\ntarget_milestone: {json.dumps({'title': pipeline_row['title'], 'description': pipeline_row['description'], 'pipeline_order': pipeline_row['pipeline_order'], 'target_weeks': pipeline_row['target_weeks']})}\n"
                    f"planning_mode: next_milestone\n"
                    f"instruction: Generate proposed_tasks ONLY for this specific milestone. "
                    f"Set goal_feasible_in_6_weeks=true and milestone_roadmap=null — the overall roadmap already exists.\n"
                )

        # Mark the currently active goal as completed
        if parent_goal_id:
            await db.execute(
                """
                UPDATE goals SET status = 'completed', completed_at = now()
                WHERE id = $1 AND user_id = $2 AND status = 'active'
                """,
                parent_goal_id,
                user_id,
            )
        else:
            # No explicit goal_id — complete whatever is currently active
            await db.execute(
                """
                UPDATE goals SET status = 'completed', completed_at = now()
                WHERE user_id = $1 AND status = 'active'
                """,
                user_id,
            )

        # Activate the pipeline goal so save_tasks can attach tasks to it
        if next_goal_id:
            await db.execute(
                """
                UPDATE goals SET status = 'active', activated_at = now()
                WHERE id = $1 AND user_id = $2
                """,
                next_goal_id,
                user_id,
            )
            goal_draft = {**goal_draft, "goal_id": next_goal_id}

    # ── Build LLM context block ───────────────────────────────────────────────
    context_block = (
        f"\n\nContext:\n"
        f"user_profile: {json.dumps(profile)}\n"
        f"classifier_output: {json.dumps(classifier_output)}\n"
        f"scheduler_output: {json.dumps(scheduler_output)}\n"
        f"pattern_output: {json.dumps(pattern_output)}\n"
        f"goal_draft: {json.dumps(goal_draft)}\n"
        f"user_preference_notes: {json.dumps(user_notes)}\n"
        + milestone_context_block
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

    # 9.2.9 — Extract new user preference notes (fire-and-forget)
    conv_history = list(state.get("conversation_history") or [])
    if conv_history:
        try:
            extract_result: UserPreferenceExtractOutput = await validated_llm_call(
                model=_MODEL_BUDGET,
                system_prompt=_PREFERENCE_EXTRACT_PROMPT,
                messages=conv_history,
                output_model=UserPreferenceExtractOutput,
                max_tokens=512,
                user_id=user_id,
            )
            for note in extract_result.notes:
                await upsert_user_note(
                    user_id=user_id,
                    key=note.key,
                    description=note.description,
                    details={
                        "activity": note.activity,
                        "days": note.days,
                        "time": note.time,
                        "duration_minutes": note.duration_minutes,
                    },
                )
        except Exception:
            # Never let note extraction break the main plan flow
            pass

    # 9.2.4 — Handle multi-sprint goals (new GOAL flow only)
    # For NEXT_MILESTONE the roadmap already exists in DB — skip re-insertion.
    if intent != "NEXT_MILESTONE" and not result.goal_feasible_in_6_weeks and result.milestone_roadmap:
        pipeline_goals = [mg for mg in result.milestone_roadmap if mg.pipeline_order > 1]
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

    # 9.2.5 — Compose assistant message from plan summary
    assistant_message = result.plan_summary

    # 9.2.6 — Append quick-action hint when plan is pending approval
    if result.approval_status == "pending":
        assistant_message += (
            "\n\n_You can accept this plan, ask me to change specific tasks or timings, "
            "or describe anything that doesn't work for you._"
        )

    # Assign stable IDs so the scheduler can echo them back for reliable matching
    # in save_tasks (avoids fragile title-string comparison).
    for i, task in enumerate(result.proposed_tasks):
        task.task_id = f"task-{i}"

    updated_draft: dict = dict(goal_draft or {})
    updated_draft["plan"] = result.model_dump()

    return {
        "goal_draft": updated_draft,
        "proposed_tasks": [t.model_dump() for t in result.proposed_tasks],
        "approval_status": result.approval_status,
        "conversation_history": conv_history
        + [{"role": "assistant", "content": assistant_message}],
    }
