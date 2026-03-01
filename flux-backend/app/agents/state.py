from typing import Annotated, Optional, TypedDict


# ─────────────────────────────────────────────────────────────────
# 5.2 — Custom reducer for sub-agent output fields
#
# When Send() dispatches classifier, scheduler, and pattern_observer
# in parallel, each node writes only its own output field. The reducer
# merges incoming partial dicts without overwriting existing keys so
# all three results land in the state correctly after reconvergence.
# ─────────────────────────────────────────────────────────────────

def _merge_dict(existing: Optional[dict], update: Optional[dict]) -> Optional[dict]:
    """Merge two optional dicts; update wins on key conflicts."""
    if existing is None:
        return update
    if update is None:
        return existing
    return {**existing, **update}


# ─────────────────────────────────────────────────────────────────
# 5.1 — AgentState TypedDict
# ─────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    user_id: str
    conversation_history: list[dict]         # Windowed — see §15 Cost Controls

    intent: Optional[str]
    user_profile: dict                        # Cached from DB at session start

    goal_draft: Optional[dict]
    proposed_tasks: Optional[list[dict]]

    # 5.2 — Annotated with merge reducer so Send() fan-out results accumulate
    classifier_output: Annotated[Optional[dict], _merge_dict]
    scheduler_output: Annotated[Optional[dict], _merge_dict]
    pattern_output: Annotated[Optional[dict], _merge_dict]

    approval_status: Optional[str]           # 'pending' | 'approved' | 'negotiating' | 'abandoned'
    error: Optional[str]
    token_usage: dict                         # Accumulated per-session token count

    # 5.3 — End-to-end trace correlation with structlog / Sentry
    correlation_id: Optional[str]
