"""Core LLM-powered pattern analysis logic for SCRUM-50.

Responsibilities
----------------
* Build a raw task-history snapshot from the DAO layer.
* Call GPT-4o-mini to extract structured behavioural patterns.
* Cold-start fallback for users with fewer than LOW_CONFIDENCE_WEEKS of data.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from openai import AsyncOpenAI

from config import settings
from logger import get_logger
from models import AvoidSlot, CategoryPerformance, PatternSummary

logger = get_logger("pattern_observer.analyzer")

# ---------------------------------------------------------------------------
# System prompt (verbatim from SCRUM-50 spec)
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """
You are a behavioral pattern analyst. Given a user's task history (completions and misses), extract meaningful scheduling patterns.

Return a structured JSON summary:
{
  "best_times": ["07:00-09:00", "18:00-19:30"],
  "avoid_slots": [
    { "day": "Monday", "time_range": "07:00-09:00", "reason": "3 consecutive misses", "confidence": 0.85 }
  ],
  "category_performance": [
    { "category": "Fitness", "completion_rate": 0.78 },
    { "category": "Learning", "completion_rate": 0.42 }
  ],
  "general_notes": "User performs best on weekday mornings. Weekend engagement drops significantly."
}

Only report patterns with at least 3 data points. Mark low-confidence patterns (< 3 weeks of data) with confidence < 0.5.
""".strip()


class PatternAnalyzer:
    """Orchestrates task-history retrieval and LLM-based pattern extraction."""

    def __init__(self) -> None:
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            logger.debug("[PatternAnalyzer] Initialising AsyncOpenAI client")
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def build_summary(
        self,
        user_id: UUID,
        tasks: List[Dict[str, Any]],
        lookback_days: int,
    ) -> PatternSummary:
        """Analyse *tasks* and return a structured PatternSummary.

        Falls back to a cold-start summary when there are fewer than
        MIN_DATA_POINTS records or the data span is below LOW_CONFIDENCE_WEEKS.
        """
        logger.info(
            "[PatternAnalyzer] Building summary | user=%s | tasks=%d | lookback=%d days",
            user_id,
            len(tasks),
            lookback_days,
        )

        low_confidence = self._is_low_confidence(tasks)

        if len(tasks) < settings.MIN_DATA_POINTS:
            logger.warning(
                "[PatternAnalyzer] Insufficient data (%d tasks) — returning cold-start summary",
                len(tasks),
            )
            return self._cold_start_summary()

        summary = await self._call_llm(user_id, tasks)
        summary.low_confidence = low_confidence

        logger.info(
            "[PatternAnalyzer] Summary built | avoid_slots=%d | best_times=%d | low_confidence=%s",
            len(summary.avoid_slots),
            len(summary.best_times),
            low_confidence,
        )
        return summary

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    async def _call_llm(self, user_id: UUID, tasks: List[Dict[str, Any]]) -> PatternSummary:
        """Send task history to GPT-4o-mini and parse the structured response."""
        user_prompt = self._build_user_prompt(tasks)
        logger.debug(
            "[PatternAnalyzer] Calling LLM | model=%s | prompt_tokens_approx=%d",
            settings.LLM_MODEL,
            len(user_prompt) // 4,
        )

        client = self._get_client()
        try:
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except Exception as exc:
            logger.error(
                "[PatternAnalyzer] LLM call failed | user=%s | error=%s",
                user_id,
                exc,
                exc_info=True,
            )
            raise

        raw = response.choices[0].message.content or "{}"
        logger.debug("[PatternAnalyzer] LLM raw response | length=%d", len(raw))

        return self._parse_llm_response(raw)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_prompt(tasks: List[Dict[str, Any]]) -> str:
        """Serialise task records into a compact JSON block for the LLM."""
        compact = [
            {
                "scheduled_at": t.get("scheduled_at", ""),
                "completed_at": t.get("completed_at"),
                "status": t.get("status", ""),
                "category": t.get("category") or t.get("trigger_type", "uncategorised"),
                "day_of_week": t.get("day_of_week", ""),
                "hour": t.get("hour"),
            }
            for t in tasks
        ]
        return (
            "Here is the user's task history for the requested period.\n"
            "Analyse it and return the JSON summary as instructed.\n\n"
            f"{json.dumps(compact, default=str)}"
        )

    @staticmethod
    def _parse_llm_response(raw: str) -> PatternSummary:
        """Parse LLM JSON into PatternSummary, gracefully handling malformed output."""
        try:
            data = json.loads(raw)
            avoid_slots = [
                AvoidSlot(**slot) for slot in data.get("avoid_slots", [])
            ]
            category_performance = [
                CategoryPerformance(**cp)
                for cp in data.get("category_performance", [])
            ]
            return PatternSummary(
                best_times=data.get("best_times", []),
                avoid_slots=avoid_slots,
                category_performance=category_performance,
                general_notes=data.get("general_notes", ""),
            )
        except Exception as exc:
            logger.error(
                "[PatternAnalyzer] Failed to parse LLM response | error=%s | raw=%s",
                exc,
                raw[:500],
                exc_info=True,
            )
            return PatternSummary()

    @staticmethod
    def _is_low_confidence(tasks: List[Dict[str, Any]]) -> bool:
        """Return True if task history covers fewer than LOW_CONFIDENCE_WEEKS weeks."""
        if not tasks:
            return True
        scheduled_dates = [
            datetime.fromisoformat(str(t["scheduled_at"]))
            for t in tasks
            if t.get("scheduled_at")
        ]
        if not scheduled_dates:
            return True
        span_days = (max(scheduled_dates) - min(scheduled_dates)).days
        threshold_days = settings.LOW_CONFIDENCE_WEEKS * 7
        return span_days < threshold_days

    @staticmethod
    def _cold_start_summary() -> PatternSummary:
        """Return a research-backed default summary for brand-new users."""
        logger.info("[PatternAnalyzer] Applying cold-start defaults")
        return PatternSummary(
            best_times=["06:00-09:00", "17:00-19:00"],
            avoid_slots=[
                AvoidSlot(
                    day="Monday",
                    time_range="07:00-09:00",
                    reason="Research-backed default: Mondays are low-energy for high-effort tasks",
                    confidence=0.3,
                )
            ],
            category_performance=[],
            general_notes=(
                "Cold-start defaults applied (fewer than "
                f"{settings.MIN_DATA_POINTS} data points). "
                "Prefer morning slots (06:00-09:00) and consistent daily times. "
                f"Patterns become meaningful after {settings.LOW_CONFIDENCE_WEEKS} weeks of data."
            ),
            low_confidence=True,
        )
