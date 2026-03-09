"""
ask_start_date node — inserted between APPROVE and save_tasks.

After the user approves a goal plan, we ask when they'd like to start.
This lets them delay the first task by a few days (e.g. "next Monday",
"in 3 days", "start from the 15th").

The user's reply is classified by the orchestrator as START_DATE intent,
which carries a parsed ISO8601 date in goal_start_date. The scheduler then
uses goal_start_date as the baseline for the first occurrence of each task.
"""

from app.agents.state import AgentState


async def ask_start_date_node(state: AgentState) -> dict:
    """
    Appends a start-date question to conversation history and ends the turn.
    The orchestrator re-enters on the user's next message and classifies it
    as START_DATE, which routes to save_tasks with goal_start_date set.
    """
    history = list(state.get("conversation_history") or [])
    question = (
        "When would you like to start? "
        'You can say "today", "tomorrow", "next Monday", or give me a specific date — '
        "and I'll schedule your first task from there."
    )
    return {
        "conversation_history": history + [{"role": "assistant", "content": question}],
        "approval_status": "awaiting_start_date",
    }
