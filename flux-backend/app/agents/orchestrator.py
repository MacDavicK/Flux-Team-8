from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import OrchestratorOutput
from app.services.llm import check_token_budget, validated_llm_call
from app.services.supabase import db

# 9.1.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "orchestrator.txt").read_text()

# Model assignments per §6.1
_MODEL_PRIMARY = "openrouter/openai/gpt-4o"
_MODEL_BUDGET = "openrouter/openai/gpt-4o-mini"


async def orchestrator_node(state: AgentState) -> dict:
    """
    Classifies the user's latest message into one of:
    GOAL | NEW_TASK | RESCHEDULE_TASK | MODIFY_GOAL | CLARIFY | ONBOARDING

    9.1.4 — If the user has not completed onboarding, intent is overridden to ONBOARDING.
    9.1.5 — If the user is over the hard token budget, model is downgraded to gpt-4o-mini.
    """
    user_id: str = state["user_id"]

    # 9.1.4 — Check onboarding status; override intent if not yet onboarded
    user_row = await db.fetchrow(
        "SELECT onboarded FROM users WHERE id = $1", user_id
    )
    if user_row and not user_row["onboarded"]:
        return {"intent": "ONBOARDING"}

    # 9.1.5 — Downgrade model on hard budget limit
    budget = await check_token_budget(user_id)
    model = _MODEL_BUDGET if budget == "hard_limit" else _MODEL_PRIMARY

    # 9.1.2 — Build messages: conversation history + user profile context
    profile = state.get("user_profile") or {}
    system = _PROMPT + (
        f"\n\nUser profile context:\n"
        f"- Timezone: {profile.get('timezone', 'UTC')}\n"
        f"- Onboarded: true\n"
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

    return {
        "intent": result.intent,
        "classifier_output": None,
        "scheduler_output": None,
        "pattern_output": None,
        "error": None,
        # Carry task_id / goal_id forward if present
        **({"goal_draft": {"goal_id": result.goal_id}} if result.goal_id else {}),
    }
