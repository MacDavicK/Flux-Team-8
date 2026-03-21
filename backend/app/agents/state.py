from typing import Annotated, Optional, TypedDict

# ─────────────────────────────────────────────────────────────────
# 5.2 — Custom reducer for sub-agent output fields
#
# When Send() dispatches classifier, scheduler, and pattern_observer
# in parallel, each node writes only its own output field. The reducer
# merges incoming partial dicts without overwriting existing keys so
# all three results land in the state correctly after reconvergence.
#
# CLEAR is a serialization-safe sentinel that means "reset this field
# to None". Use it instead of None when an intentional reset is needed
# (e.g. orchestrator clearing stale sub-agent outputs before a new
# fan-out). A plain None update is treated as a no-op so sub-agents
# that don't write a field don't accidentally clear it.
# ─────────────────────────────────────────────────────────────────

CLEAR = "__CLEAR__"


def _merge_dict(existing: Optional[dict], update: Optional[dict]) -> Optional[dict]:
    """Merge two optional dicts; update wins on key conflicts.

    Special values:
    - update is None     → no-op (sub-agent didn't touch this field)
    - update == CLEAR    → hard reset to None (intentional clear)
    """
    if update is None:
        return existing
    if update == CLEAR:
        return None
    if existing is None:
        return update
    return {**existing, **update}


# ─────────────────────────────────────────────────────────────────
# 5.1 — AgentState TypedDict
# ─────────────────────────────────────────────────────────────────


class AgentState(TypedDict):
    user_id: str
    conversation_history: list[dict]  # Windowed — see §15 Cost Controls

    intent: Optional[str]
    user_profile: dict  # Cached from DB at session start

    goal_draft: Optional[dict]
    proposed_tasks: Optional[list[dict]]

    # 5.2 — Annotated with merge reducer so Send() fan-out results accumulate
    classifier_output: Annotated[Optional[dict], _merge_dict]
    scheduler_output: Annotated[Optional[dict], _merge_dict]
    pattern_output: Annotated[Optional[dict], _merge_dict]
    # RAG retrieval output — shape: {context: str, sources: list[dict], retrieved: bool}
    rag_output: Annotated[Optional[dict], _merge_dict]

    clarification_question: Optional[str]  # Set by orchestrator when intent == CLARIFY
    approval_status: Optional[
        str
    ]  # 'pending' | 'approved' | 'awaiting_start_date' | 'negotiating' | 'abandoned'
    goal_start_date: Optional[
        str
    ]  # ISO8601 date the user wants to start (set after approval start-date question)
    milestone_order: Optional[
        int
    ]  # Set when intent == NEXT_MILESTONE; which pipeline_order to plan
    error: Optional[str]
    token_usage: dict  # Accumulated per-session token count

    # 5.3 — End-to-end trace correlation with structlog / Sentry
    correlation_id: Optional[str]

    # Conversation DB UUID — used by save_tasks to cancel superseded NEW_TASK rows
    conversation_id: Optional[str]

    # Quick-select options shown below the latest assistant message (UI-only, not persisted)
    options: Optional[list]
