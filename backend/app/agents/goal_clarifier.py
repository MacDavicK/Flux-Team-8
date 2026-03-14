from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import GoalClarifierOutput
from app.services.llm import check_token_budget, validated_llm_call

_PROMPT = (Path(__file__).parent / "prompts" / "goal_clarifier.txt").read_text()

# Always use budget model — question generation is a lightweight task
_MODEL = "openrouter/openai/gpt-4o-mini"


async def goal_clarifier_node(state: AgentState) -> dict:
    """
    Determines whether the user's goal needs clarifying questions before planning.

    Entry paths:
    - intent == "GOAL" (first visit): calls LLM to generate questions or skip to planning.
    - intent == "GOAL_CLARIFY" (user submitted answers): stores answers in goal_draft,
      sets intent to GOAL_PLAN so route_from_goal_clarifier routes to goal_planner.

    Returns:
    - If questions needed: intent "GOAL_CLARIFY" + options (question list) + updated goal_draft
    - If no questions / answers already present: intent "GOAL_PLAN" (empty dict triggers routing)
    """
    user_id: str = state["user_id"]
    goal_draft: dict = dict(state.get("goal_draft") or {})

    # ── GOAL_CLARIFY: user submitted answers from frontend ────────────────────
    # The answers arrive as body.answers in the API, stored in goal_draft by chat.py.
    # Presence of clarification_answers means we have all context — proceed to planning.
    if state.get("intent") == "GOAL_CLARIFY":
        return {"intent": "GOAL_PLAN"}

    # ── GOAL: first visit — determine if we need clarification ───────────────
    budget = await check_token_budget(user_id)
    # Always use budget model regardless — this is a cheap classification call
    _ = budget  # budget check preserved for future use

    result: GoalClarifierOutput = await validated_llm_call(
        model=_MODEL,
        system_prompt=_PROMPT,
        messages=list(state.get("conversation_history") or []),
        output_model=GoalClarifierOutput,
        max_tokens=1024,
        user_id=user_id,
    )

    # No questions needed — enough context to plan immediately
    if not result.questions:
        return {"intent": "GOAL_PLAN"}

    # Store generated questions in goal_draft so goal_planner has them as context
    goal_draft["clarification_questions"] = [q.model_dump() for q in result.questions]

    # Build a brief assistant message acknowledging the goal
    # The real question rendering happens in the frontend via the options payload
    history = list(state.get("conversation_history") or [])
    assistant_message = (
        "To help me build the best plan for you, I have a few quick questions."
    )

    return {
        "intent": "GOAL_CLARIFY",
        "goal_draft": goal_draft,
        "conversation_history": history
        + [{"role": "assistant", "content": assistant_message}],
        # options carries the structured question list for the frontend
        "options": [q.model_dump() for q in result.questions],
    }
