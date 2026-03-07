"""
10. LangGraph Graph Assembly — §7.

Assembles the complete agent graph with all nodes, edges, conditional routing
functions, Send()-based fan-out, and the AsyncPostgresSaver checkpointer.

Stub nodes for tasks 11.1–11.3 (task_handler, save_tasks, goal_modifier) are
included as minimal placeholders to be replaced when those tasks are done.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send
from psycopg_pool import AsyncConnectionPool

from app.agents.ask_start_date import ask_start_date_node
from app.agents.classifier import classifier_node
from app.agents.goal_clarifier import goal_clarifier_node
from app.agents.goal_planner import goal_planner_node
from app.agents.onboarding import onboarding_node
from app.agents.orchestrator import orchestrator_node
from app.agents.pattern_observer import pattern_observer_node
from app.agents.scheduler import scheduler_node
from app.agents.state import AgentState
from app.agents.task_handler import task_handler_node   # 11.1
from app.agents.save_tasks import save_tasks_node       # 11.2
from app.agents.goal_modifier import goal_modifier_node  # 11.3
from app.config import settings


# ─────────────────────────────────────────────────────────────────
# Clarify node (implied by 10.3 / 10.4)
# ─────────────────────────────────────────────────────────────────


async def chitchat_node(state: AgentState) -> dict:
    """
    Handles greetings and generic messages by responding politely and
    letting the user know what Flux can help with.
    """
    history = list(state.get("conversation_history") or [])
    reply = (
        "Hi there! I'm Flux, your personal goal and task assistant. "
        "I can help you set goals, break them into actionable tasks, and keep you on track. "
        "Try telling me something like \"I want to run a 5K\" or \"Remind me to drink water every morning\"."
    )
    return {
        "conversation_history": history + [
            {"role": "assistant", "content": reply}
        ],
        "intent": None,
    }


async def clarify_node(state: AgentState) -> dict:
    """
    Asks a clarifying question and loops back to the orchestrator (10.4).
    """
    question = state.get("clarification_question") or "Could you give me a bit more detail? For example, a specific time or what you'd like to achieve."
    history = list(state.get("conversation_history") or [])
    return {
        "conversation_history": history + [
            {"role": "assistant", "content": question}
        ],
        "intent": None,
    }


# ─────────────────────────────────────────────────────────────────
# 10.3 — Orchestrator routing
# ─────────────────────────────────────────────────────────────────


def route_from_orchestrator(state: AgentState) -> str:
    """Routes from orchestrator to the appropriate agent based on intent."""
    approval = state.get("approval_status") or ""

    # User just approved — ask when they want to start before saving tasks.
    if approval == "approved" and state.get("proposed_tasks") and not state.get("goal_start_date"):
        return "ask_start_date"

    # User answered the start-date question — re-run scheduler with the new
    # start date, then save tasks.
    if approval == "approved" and state.get("proposed_tasks") and state.get("goal_start_date"):
        return "reschedule"

    intent = state.get("intent") or ""

    # MODIFY_GOAL while still in negotiation (goal not yet saved to DB — no
    # goal_id in goal_draft) means the user wants to change the *draft* plan.
    # Re-route to goal_planner so it re-plans with the new information.
    if intent == "MODIFY_GOAL":
        goal_draft = state.get("goal_draft") or {}
        if not goal_draft.get("goal_id"):
            return "goal_planner"

    return {
        "ONBOARDING":     "onboarding",
        "GOAL":           "goal_clarifier",  # always goes through clarifier first
        "GOAL_CLARIFY":   "goal_clarifier",  # frontend submitted answers batch
        "NEW_TASK":       "task_handler",
        "MODIFY_GOAL":    "goal_modifier",
        "NEXT_MILESTONE": "goal_planner",    # milestone skips clarifier
        "CHITCHAT":       "chitchat",
        "CLARIFY":        "clarify",
    }.get(intent, "chitchat")


# ─────────────────────────────────────────────────────────────────
# 10.6 + 10.8 — Goal planner routing (fan-out + approval)
# ─────────────────────────────────────────────────────────────────


def route_from_goal_clarifier(state: AgentState) -> str:
    """
    Routes from goal_clarifier:
    - GOAL_PLAN  → goal_planner (enough context gathered)
    - otherwise  → END (questions sent to frontend; user answers on next turn)
    """
    if state.get("intent") == "GOAL_PLAN":
        return "goal_planner"
    return END


def route_from_goal_planner(state: AgentState) -> str | list[Send]:
    """
    Combined routing from goal_planner covering tasks 10.6 and 10.8.

    First call (no sub-agent outputs yet): fan out via Send() for true parallel
    execution of classifier, scheduler, and pattern_observer (10.6).

    Subsequent calls (all sub-agent outputs present): check user approval (10.8).
      APPROVED  → save_tasks
      ABANDONED → END
      otherwise → END  (NEGOTIATING: state preserved; re-entered on next user message)
    """
    classifier_done = state.get("classifier_output") is not None
    scheduler_done = state.get("scheduler_output") is not None
    pattern_done = state.get("pattern_output") is not None

    if not (classifier_done and scheduler_done and pattern_done):
        # 10.6 — Fan out: pass each sub-agent the state slice it needs
        user_id = state["user_id"]
        goal_draft = state.get("goal_draft") or {}
        user_profile = state.get("user_profile") or {}
        conv_history = state.get("conversation_history") or []
        token_usage = state.get("token_usage") or {}

        return [
            Send("classifier", {
                "user_id": user_id,
                "goal_draft": goal_draft,
                "user_profile": user_profile,
                "conversation_history": conv_history,
                "token_usage": token_usage,
            }),
            Send("scheduler", {
                "user_id": user_id,
                "goal_draft": goal_draft,
                "user_profile": user_profile,
                "conversation_history": conv_history,
                "token_usage": token_usage,
            }),
            Send("pattern_observer", {
                "user_id": user_id,
                "goal_draft": goal_draft,
                "user_profile": user_profile,
                "conversation_history": conv_history,
                "token_usage": token_usage,
            }),
        ]

    # 10.8 — Approval check after all sub-agents have reported
    approval = state.get("approval_status") or "negotiating"
    if approval == "approved":
        # Route via ask_start_date unless a start date was already provided
        if state.get("goal_start_date"):
            return "save_tasks"
        return "ask_start_date"
    if approval == "abandoned":
        return END
    # NEGOTIATING — end this turn; orchestrator re-routes on next user message
    return END


# ─────────────────────────────────────────────────────────────────
# 10.1 — Assemble graph
# ─────────────────────────────────────────────────────────────────


def _build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # 10.1 — Register all nodes
    graph.add_node("orchestrator",     orchestrator_node)
    graph.add_node("chitchat",         chitchat_node)
    graph.add_node("clarify",          clarify_node)
    graph.add_node("onboarding",       onboarding_node)
    graph.add_node("goal_clarifier",   goal_clarifier_node)
    graph.add_node("goal_planner",     goal_planner_node)
    graph.add_node("classifier",       classifier_node)
    graph.add_node("scheduler",        scheduler_node)
    graph.add_node("pattern_observer", pattern_observer_node)
    graph.add_node("task_handler",     task_handler_node)
    graph.add_node("goal_modifier",    goal_modifier_node)
    graph.add_node("save_tasks",       save_tasks_node)
    graph.add_node("ask_start_date",   ask_start_date_node)
    # reschedule reuses scheduler_node but runs standalone (not via Send fan-out)
    # so save_tasks gets fresh slots anchored to goal_start_date.
    graph.add_node("reschedule",       scheduler_node)

    # 10.2 — Entry point
    graph.set_entry_point("orchestrator")

    # 10.3 — Orchestrator → appropriate agent
    graph.add_conditional_edges("orchestrator", route_from_orchestrator)

    # chitchat ends the turn; user's next message re-enters via orchestrator
    graph.add_edge("chitchat", END)

    # 10.4 — clarify ends the turn; user's next message re-enters via orchestrator
    graph.add_edge("clarify", END)

    # 10.5 — onboarding ends each turn (state persisted in checkpointer).
    # The completion transition message is written to conversation_history by
    # onboarding_node; the user's next message naturally re-enters via the
    # orchestrator entry point ("re-route after completion" per §10.5).
    graph.add_edge("onboarding", END)

    # goal_clarifier: either sends questions to frontend (→ END) or proceeds to
    # goal_planner when intent is GOAL_PLAN (enough context gathered / answers received)
    graph.add_conditional_edges("goal_clarifier", route_from_goal_clarifier)

    # 10.6 — goal_planner fans out via Send() on first call
    # 10.7 — classifier/scheduler/pattern_observer reconverge to goal_planner
    # 10.8 — goal_planner checks approval after sub-agents complete
    graph.add_conditional_edges("goal_planner", route_from_goal_planner)
    graph.add_edge("classifier",       "goal_planner")
    graph.add_edge("scheduler",        "goal_planner")
    graph.add_edge("pattern_observer", "goal_planner")

    # 10.9 — Terminal edges
    graph.add_edge("save_tasks",      END)
    graph.add_edge("task_handler",    "save_tasks")
    graph.add_edge("goal_modifier",   "save_tasks")
    # ask_start_date ends the turn; user's next message re-enters via orchestrator
    graph.add_edge("ask_start_date",  END)
    # reschedule → save_tasks: fresh slots anchored to goal_start_date
    graph.add_edge("reschedule",      "save_tasks")

    return graph


# ─────────────────────────────────────────────────────────────────
# 10.10 — AsyncPostgresSaver checkpointer
# ─────────────────────────────────────────────────────────────────


def _psycopg_dsn() -> str:
    """Return plain postgresql:// DSN for psycopg (strips +asyncpg dialect if present)."""
    return (
        settings.database_url
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgres+asyncpg://", "postgresql://")
    )


@asynccontextmanager
async def checkpointer_lifespan() -> AsyncIterator[AsyncPostgresSaver]:
    """
    10.10 — Async context manager that yields a ready AsyncPostgresSaver.

    Uses an AsyncConnectionPool so stale/dropped connections are automatically
    replaced — avoids 'SSL SYSCALL error: EOF detected' on idle connections.

    NOTE: direct port 5432 only (NOT PgBouncer 6543) — transaction-mode pooling
    is incompatible with LangGraph checkpoint writes.
    """
    async with AsyncConnectionPool(
        conninfo=_psycopg_dsn(),
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True},
    ) as pool:
        cp = AsyncPostgresSaver(conn=pool)
        await cp.setup()
        yield cp


# ─────────────────────────────────────────────────────────────────
# 10.11 — Compile and expose compiled_graph
# ─────────────────────────────────────────────────────────────────

# Compiled without a checkpointer at import time — suitable for unit tests and
# local single-turn use. The FastAPI lifespan (task 18.7) re-compiles this with
# a live AsyncPostgresSaver to enable multi-turn state persistence.
compiled_graph = _build_graph().compile()
