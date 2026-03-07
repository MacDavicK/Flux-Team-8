"""
Flux Backend — Orchestrator Agent

Routes a user message to the right specialized capability:
- Goal Planner (start / continue goal conversation)
- Scheduler (list tasks / suggest reschedule / apply reschedule)

This is intentionally deterministic for MVP reliability.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TypedDict

from app.models.schemas import OrchestratorIntent, OrchestratorMessageRequest

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorDecision:
    intent: OrchestratorIntent
    route: str
    reason: str


class OrchestratorAgent:
    """Deterministic intent router for Flux MVP."""

    class _GraphState(TypedDict, total=False):
        body: OrchestratorMessageRequest
        decision: OrchestratorDecision

    _TASK_HINTS = (
        "today tasks",
        "my tasks",
        "show tasks",
        "timeline",
        "calendar",
        "what do i have",
    )

    _RESCHEDULE_HINTS = (
        "reschedule",
        "move",
        "drift",
        "missed",
        "suggest slot",
        "new time",
        "postpone",
    )

    _SKIP_HINTS = ("skip", "miss this", "can't do this")

    _UUID_PATTERN = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )

    def __init__(self, use_langgraph: bool = False):
        self._use_langgraph = use_langgraph
        self._graph = self._build_langgraph() if use_langgraph else None

    def decide(self, body: OrchestratorMessageRequest) -> OrchestratorDecision:
        if self._use_langgraph and self._graph is not None:
            try:
                result = self._graph.invoke({"body": body})
                decision = result.get("decision")
                if isinstance(decision, OrchestratorDecision):
                    return decision
            except Exception as exc:
                logger.warning("LangGraph orchestrator failed; using fallback: %s", exc)

        return self._decide_deterministic(body)

    def _decide_deterministic(
        self, body: OrchestratorMessageRequest
    ) -> OrchestratorDecision:
        text = (body.message or "").strip().lower()

        # 0) Explicit voice action override
        voice_action = (body.voice_action or "").strip().lower()
        if voice_action == "create_session":
            return OrchestratorDecision(
                intent=OrchestratorIntent.VOICE_CREATE_SESSION,
                route="voice.session.create",
                reason="Explicit voice action override",
            )
        if voice_action == "save_message":
            return OrchestratorDecision(
                intent=OrchestratorIntent.VOICE_SAVE_MESSAGE,
                route="voice.messages.save",
                reason="Explicit voice action override",
            )
        if voice_action == "get_messages":
            return OrchestratorDecision(
                intent=OrchestratorIntent.VOICE_GET_MESSAGES,
                route="voice.messages.get",
                reason="Explicit voice action override",
            )
        if voice_action == "process_intent":
            return OrchestratorDecision(
                intent=OrchestratorIntent.VOICE_PROCESS_INTENT,
                route="voice.intents.process",
                reason="Explicit voice action override",
            )
        if voice_action == "close_session":
            return OrchestratorDecision(
                intent=OrchestratorIntent.VOICE_CLOSE_SESSION,
                route="voice.session.close",
                reason="Explicit voice action override",
            )

        # 1) Explicit action override for scheduler apply
        if body.action in {"reschedule", "skip"} and body.event_id:
            return OrchestratorDecision(
                intent=OrchestratorIntent.APPLY_RESCHEDULE,
                route="scheduler.apply",
                reason="Explicit scheduler action provided",
            )

        # 2) Goal conversation continuation always wins if conversation_id exists
        if body.conversation_id:
            return OrchestratorDecision(
                intent=OrchestratorIntent.CONTINUE_GOAL,
                route="goals.respond",
                reason="conversation_id present",
            )

        # 3) Task listing intent
        if any(hint in text for hint in self._TASK_HINTS):
            return OrchestratorDecision(
                intent=OrchestratorIntent.LIST_TASKS,
                route="scheduler.tasks",
                reason="Task-listing phrase detected",
            )

        # 4) Scheduler suggest/apply via event_id + keywords
        event_id = body.event_id or self.extract_event_id(text)
        if event_id:
            if any(hint in text for hint in self._SKIP_HINTS):
                return OrchestratorDecision(
                    intent=OrchestratorIntent.APPLY_RESCHEDULE,
                    route="scheduler.apply",
                    reason="Skip keyword with event id",
                )

            if any(hint in text for hint in self._RESCHEDULE_HINTS):
                return OrchestratorDecision(
                    intent=OrchestratorIntent.SUGGEST_RESCHEDULE,
                    route="scheduler.suggest",
                    reason="Reschedule phrase with event id",
                )

        # 5) Default to starting a goal conversation
        return OrchestratorDecision(
            intent=OrchestratorIntent.START_GOAL,
            route="goals.start",
            reason="Default route",
        )

    def _extract_uuid(self, text: str) -> str | None:
        match = self._UUID_PATTERN.search(text)
        return match.group(0) if match else None

    def extract_event_id(self, text: str) -> str | None:
        """Public helper for extracting UUID event IDs from text."""
        return self._extract_uuid(text)

    def _build_langgraph(self):
        """Build a minimal LangGraph around existing routing logic.

        This keeps behavior identical while enabling a graph-based orchestrator
        path behind a feature flag.
        """
        try:
            from langgraph.graph import END, StateGraph

            def classify_node(state: OrchestratorAgent._GraphState):
                body = state["body"]
                return {"decision": self._decide_deterministic(body)}

            workflow = StateGraph(OrchestratorAgent._GraphState)
            workflow.add_node("classify", classify_node)
            workflow.set_entry_point("classify")
            workflow.add_edge("classify", END)
            return workflow.compile()

        except Exception as exc:
            logger.warning(
                "LangGraph unavailable; orchestrator will use deterministic mode: %s",
                exc,
            )
            return None
