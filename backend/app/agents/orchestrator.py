import uuid
from pathlib import Path

import pendulum

from app.agents.state import AgentState
from app.models.agent_outputs import OrchestratorOutput
from app.services.llm import check_token_budget, validated_llm_call
from app.services.supabase import db

# 9.1.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "orchestrator.txt").read_text()

# Model assignments per §6.1
_MODEL_PRIMARY = "openrouter/openai/gpt-4o"
_MODEL_BUDGET = "openrouter/openai/gpt-4o-mini"


def _parse_start_date(payload: dict, messages: list, user_tz: str) -> str:
    """
    Extract the ISO8601 start date from the orchestrator payload or fall back
    to parsing the user's last message with pendulum. Returns today's date in
    the user's timezone if nothing can be parsed.
    """
    # Orchestrator may put the parsed date directly in payload
    raw = payload.get("start_date") or payload.get("date") or ""
    if not raw and messages:
        # Grab the last user turn text as a fallback
        for msg in reversed(messages):
            if msg.get("role") == "user":
                raw = msg.get("content", "")
                break

    tz = pendulum.timezone(user_tz)
    now_local = pendulum.now(tz)

    if raw:
        # Handle natural-language keywords
        lower = raw.strip().lower()
        if lower in ("today", "now"):
            return now_local.to_date_string()
        if lower in ("tomorrow",):
            return now_local.add(days=1).to_date_string()
        # Try to parse as an ISO date or free-form date string
        try:
            dt = pendulum.parse(raw, tz=tz)
            return dt.to_date_string()
        except Exception:
            pass

    return now_local.to_date_string()


async def orchestrator_node(state: AgentState) -> dict:
    """
    Classifies the user's latest message into one of:
    GOAL | NEW_TASK | RESCHEDULE_TASK | MODIFY_GOAL | NEXT_MILESTONE | CHITCHAT | CLARIFY | ONBOARDING

    9.1.4 — If the user has not completed onboarding, intent is overridden to ONBOARDING.
    9.1.5 — If the user is over the hard token budget, model is downgraded to gpt-4o-mini.
    """
    user_id: str = state["user_id"]

    # 9.1.4 — Check onboarding status; override intent if not yet onboarded
    user_row = await db.fetchrow(
        "SELECT onboarded FROM users WHERE id = $1", uuid.UUID(user_id)
    )
    if user_row and not user_row["onboarded"]:
        return {"intent": "ONBOARDING"}

    # 9.1.5 — Downgrade model on hard budget limit
    budget = await check_token_budget(user_id)
    model = _MODEL_BUDGET if budget == "hard_limit" else _MODEL_PRIMARY

    # 9.1.2 — Build messages: conversation history + user profile context
    profile = state.get("user_profile") or {}
    approval_status = state.get("approval_status") or ""
    system = _PROMPT + (
        f"\n\nUser profile context:\n"
        f"- Timezone: {profile.get('timezone', 'UTC')}\n"
        f"- Onboarded: true\n"
        f"- approval_status: {approval_status or 'none'}\n"
    )
    messages = list(state.get("conversation_history") or [])

    # 9.1.3 — Call validated LLM; parse into OrchestratorOutput
    result: OrchestratorOutput = await validated_llm_call(
        model=model,
        system_prompt=system,
        messages=messages,
        output_model=OrchestratorOutput,
        max_tokens=512,
        user_id=user_id,
    )

    # APPROVE intent: user confirmed a pending plan — ask when they want to start.
    # route_from_orchestrator will route to ask_start_date.
    if result.intent == "APPROVE":
        return {"approval_status": "approved"}

    # START_DATE intent: user replied to the start-date question.
    # Parse their reply into an ISO8601 date and route to save_tasks.
    if result.intent == "START_DATE":
        user_tz = profile.get("timezone", "UTC")
        goal_start_date = _parse_start_date(result.payload, messages, user_tz)
        return {
            "approval_status": "approved",
            "goal_start_date": goal_start_date,
        }

    out: dict = {
        "intent": result.intent,
        "clarification_question": result.clarification_question,
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "milestone_order": None,
        "error": None,
    }

    # Carry goal_id / milestone_order into goal_draft for downstream nodes
    if result.intent == "NEXT_MILESTONE":
        goal_draft: dict = {}
        if result.goal_id:
            goal_draft["goal_id"] = result.goal_id
        if result.milestone_order is not None:
            goal_draft["milestone_order"] = result.milestone_order
        out["goal_draft"] = goal_draft
        out["milestone_order"] = result.milestone_order
    elif result.goal_id:
        out["goal_draft"] = {"goal_id": result.goal_id}

    return out
