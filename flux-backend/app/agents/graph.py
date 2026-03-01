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

from app.agents.classifier import classifier_node
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


async def clarify_node(state: AgentState) -> dict:
    """
    Asks a clarifying question and loops back to the orchestrator (10.4).
    """
    history = list(state.get("conversation_history") or [])
    return {
        "conversation_history": history + [
            {"role": "assistant", "content": "Could you clarify what you mean?"}
        ],
        "intent": None,
    }


# ─────────────────────────────────────────────────────────────────
# 10.3 — Orchestrator routing
# ─────────────────────────────────────────────────────────────────


def route_from_orchestrator(state: AgentState) -> str:
    """Routes from orchestrator to the appropriate agent based on intent."""
    intent = state.get("intent") or ""
    return {
        "ONBOARDING":      "onboarding",
        "GOAL":            "goal_planner",
        "NEW_TASK":        "task_handler",
        "RESCHEDULE_TASK": "scheduler",
        "MODIFY_GOAL":     "goal_modifier",
        "CLARIFY":         "clarify",
    }.get(intent, "clarify")


# ─────────────────────────────────────────────────────────────────
# 10.6 + 10.8 — Goal planner routing (fan-out + approval)
# ─────────────────────────────────────────────────────────────────


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
        return "save_tasks"
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
    graph.add_node("clarify",          clarify_node)
    graph.add_node("onboarding",       onboarding_node)
    graph.add_node("goal_planner",     goal_planner_node)
    graph.add_node("classifier",       classifier_node)
    graph.add_node("scheduler",        scheduler_node)
    graph.add_node("pattern_observer", pattern_observer_node)
    graph.add_node("task_handler",     task_handler_node)
    graph.add_node("goal_modifier",    goal_modifier_node)
    graph.add_node("save_tasks",       save_tasks_node)

    # 10.2 — Entry point
    graph.set_entry_point("orchestrator")

    # 10.3 — Orchestrator → appropriate agent
    graph.add_conditional_edges("orchestrator", route_from_orchestrator)

    # 10.4 — clarify loops back to orchestrator after its question
    graph.add_edge("clarify", "orchestrator")

    # 10.5 — onboarding ends each turn (state persisted in checkpointer).
    # The completion transition message is written to conversation_history by
    # onboarding_node; the user's next message naturally re-enters via the
    # orchestrator entry point ("re-route after completion" per §10.5).
    graph.add_edge("onboarding", END)

    # 10.6 — goal_planner fans out via Send() on first call
    # 10.7 — classifier/scheduler/pattern_observer reconverge to goal_planner
    # 10.8 — goal_planner checks approval after sub-agents complete
    graph.add_conditional_edges("goal_planner", route_from_goal_planner)
    graph.add_edge("classifier",       "goal_planner")
    graph.add_edge("scheduler",        "goal_planner")
    graph.add_edge("pattern_observer", "goal_planner")

    # 10.9 — Terminal edges
    graph.add_edge("save_tasks",    END)
    graph.add_edge("task_handler",  "save_tasks")
    graph.add_edge("goal_modifier", "save_tasks")

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

    Opens a psycopg connection to Postgres on the direct port 5432 (NOT PgBouncer
    6543 — transaction-mode pooling is incompatible with LangGraph checkpoint writes).
    Runs setup() to create checkpoint tables if absent, then yields the saver.

    Intended for use inside the FastAPI lifespan (task 18.7):

        async with checkpointer_lifespan() as cp:
            graph_module.compiled_graph = _build_graph().compile(checkpointer=cp)
            yield  # app handles requests; psycopg connection stays alive
    """
    async with AsyncPostgresSaver.from_conn_string(_psycopg_dsn()) as cp:
        await cp.setup()
        yield cp


# ─────────────────────────────────────────────────────────────────
# 10.11 — Compile and expose compiled_graph
# ─────────────────────────────────────────────────────────────────

# Compiled without a checkpointer at import time — suitable for unit tests and
# local single-turn use. The FastAPI lifespan (task 18.7) re-compiles this with
# a live AsyncPostgresSaver to enable multi-turn state persistence.
compiled_graph = _build_graph().compile()
