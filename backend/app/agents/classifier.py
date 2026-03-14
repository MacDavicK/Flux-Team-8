from pathlib import Path

from app.agents.state import AgentState
from app.models.agent_outputs import ClassifierOutput
from app.services.llm import validated_llm_call

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

    # goal_draft has no title/description during the fan-out phase (those fields
    # are only populated after goal_planner runs). Fall back to the user's latest
    # message from conversation_history so the classifier has something to work with.
    if not goal_text:
        history = state.get("conversation_history") or []
        for msg in reversed(history):
            if msg.get("role") == "user":
                goal_text = msg.get("content", "")
                break

    # 9.3.2 — Call validated LLM with ClassifierOutput, max_tokens=128
    result: ClassifierOutput = await validated_llm_call(
        model=_MODEL,
        system_prompt=_PROMPT,
        messages=[{"role": "user", "content": f"Goal: {goal_text}"}],
        output_model=ClassifierOutput,
        max_tokens=128,
        user_id=user_id,
    )

    # 9.3.3 — class_tags are written to the goal row by save_tasks_node after the
    # goal row is created (new goals have no goal_id yet at this point).
    return {"classifier_output": {"tags": result.tags}}
