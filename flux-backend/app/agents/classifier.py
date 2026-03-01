from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import ClassifierOutput
from app.services.llm import validated_llm_call
from app.services.supabase import db

# 9.3.1 — Load system prompt once at import time
_PROMPT = (Path(__file__).parent / "prompts" / "classifier.txt").read_text()

_MODEL = "openrouter/openai/gpt-4o-mini"


async def classifier_node(state: AgentState) -> dict:
    """
    Tags the goal with 1–3 category labels from the fixed 14-tag taxonomy.
    Writes class_tags back to the goal row in DB.
    """
    user_id: str = state["user_id"]
    goal_draft: dict = state.get("goal_draft") or {}

    goal_text = goal_draft.get("title") or goal_draft.get("description") or ""

    # 9.3.2 — Call validated LLM with ClassifierOutput, max_tokens=128
    result: ClassifierOutput = await validated_llm_call(
        model=_MODEL,
        system_prompt=_PROMPT,
        messages=[{"role": "user", "content": f"Goal: {goal_text}"}],
        output_model=ClassifierOutput,
        max_tokens=128,
        user_id=user_id,
    )

    # 9.3.3 — Write class_tags back to the goal row in DB
    goal_id = goal_draft.get("goal_id")
    if goal_id:
        await db.execute(
            "UPDATE goals SET class_tags = $1 WHERE id = $2 AND user_id = $3",
            result.tags,
            goal_id,
            user_id,
        )

    return {"classifier_output": {"tags": result.tags}}
