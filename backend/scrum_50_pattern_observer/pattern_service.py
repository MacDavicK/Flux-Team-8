"""Service layer for the Pattern Observer agent (SCRUM-50).

Handles:
  - Consultation requests (summarise behavioural history for Goal Planner / Scheduler)
  - Task-miss signal processing (avoidance-slot detection + DAO writes)
  - DAO interactions via dao_service HTTP client
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from config import settings
from logger import get_logger
from models import (
    ConsultationRequest,
    ConsultationResponse,
    MissSignalResponse,
    PatternSummary,
    TaskMissSignal,
)
from pattern_analyzer import PatternAnalyzer

logger = get_logger("pattern_observer.service")

# Base URL of the DAO service (running as a sidecar / sibling container)
_DAO_BASE = "http://localhost:8000"


class PatternService:
    """Coordinates DAO calls and LLM analysis."""

    def __init__(self) -> None:
        self._analyzer = PatternAnalyzer()
        self._http: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # HTTP client lifecycle
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(base_url=_DAO_BASE, timeout=15.0)
            logger.debug("[PatternService] HTTP client initialised | base=%s", _DAO_BASE)
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            logger.debug("[PatternService] HTTP client closed")

    # ------------------------------------------------------------------
    # Consultation endpoint handler
    # ------------------------------------------------------------------

    async def consult(
        self, request: ConsultationRequest
    ) -> ConsultationResponse:
        """Return a structured pattern summary for the given user."""
        logger.info(
            "[PatternService] Consultation request | user=%s | lookback=%s days",
            request.user_id,
            request.lookback_days or settings.TASK_HISTORY_DAYS,
        )

        lookback = request.lookback_days or settings.TASK_HISTORY_DAYS
        tasks = await self._fetch_task_history(request.user_id, lookback)
        summary = await self._analyzer.build_summary(request.user_id, tasks, lookback)

        logger.info(
            "[PatternService] Consultation complete | user=%s | tasks_analysed=%d",
            request.user_id,
            len(tasks),
        )
        return ConsultationResponse(
            user_id=request.user_id,
            pattern_summary=summary,
            data_points_analysed=len(tasks),
        )

    # ------------------------------------------------------------------
    # Task-miss signal handler
    # ------------------------------------------------------------------

    async def handle_miss_signal(
        self, signal: TaskMissSignal
    ) -> MissSignalResponse:
        """Update pattern records when a task is marked as missed.

        If the same time-slot (±SLOT_TOLERANCE_HOURS, same day of week) has
        been missed ≥ AVOIDANCE_MISS_THRESHOLD times in
        AVOIDANCE_WEEK_SPAN consecutive weeks, an avoidance pattern is
        created / updated via the DAO service.
        """
        logger.info(
            "[PatternService] Miss signal received | user=%s | task=%s | scheduled=%s | category=%s",
            signal.user_id,
            signal.task_id,
            signal.scheduled_at.isoformat(),
            signal.category,
        )

        avoidance_flagged, pattern_id = await self._check_and_flag_avoidance(signal)

        msg = (
            f"Avoidance pattern flagged for slot "
            f"{signal.scheduled_at.strftime('%A %H:%M')}."
            if avoidance_flagged
            else "Miss signal recorded. Monitoring for recurring avoidance."
        )

        logger.info(
            "[PatternService] Miss signal processed | user=%s | avoidance=%s | pattern_id=%s",
            signal.user_id,
            avoidance_flagged,
            pattern_id,
        )
        return MissSignalResponse(
            user_id=signal.user_id,
            task_id=signal.task_id,
            avoidance_flagged=avoidance_flagged,
            pattern_id=pattern_id,
            message=msg,
        )

    # ------------------------------------------------------------------
    # Internal: avoidance detection logic
    # ------------------------------------------------------------------

    async def _check_and_flag_avoidance(
        self, signal: TaskMissSignal
    ) -> tuple[bool, Optional[UUID]]:
        """Detect ≥3 misses in the same slot across 3 consecutive weeks.

        Returns (flagged, pattern_id).
        """
        target_day = signal.scheduled_at.strftime("%A")
        target_hour = signal.scheduled_at.hour
        tolerance = settings.SLOT_TOLERANCE_HOURS
        lookback_days = settings.AVOIDANCE_WEEK_SPAN * 7 + 7  # small buffer

        logger.debug(
            "[PatternService] Checking avoidance | user=%s | day=%s | hour=%d ±%d",
            signal.user_id,
            target_day,
            target_hour,
            tolerance,
        )

        # Fetch missed tasks within the relevant window from dao_service
        try:
            tasks = await self._fetch_task_history(
                signal.user_id, lookback_days, status_filter="missed"
            )
        except Exception as exc:
            logger.error(
                "[PatternService] Failed to fetch task history for avoidance check | error=%s",
                exc,
                exc_info=True,
            )
            return False, None

        # Filter to tasks in the matching slot
        matching = [
            t for t in tasks
            if (
                t.get("day_of_week") == target_day
                and t.get("hour") is not None
                and abs(int(t["hour"]) - target_hour) <= tolerance
            )
        ]

        # Include the current signal
        miss_count = len(matching) + 1  # +1 for the signal just arrived

        logger.debug(
            "[PatternService] Slot miss history | user=%s | day=%s | hour=%d | prior_misses=%d | total=%d",
            signal.user_id,
            target_day,
            target_hour,
            len(matching),
            miss_count,
        )

        if miss_count < settings.AVOIDANCE_MISS_THRESHOLD:
            return False, None

        # Check the misses span ≥ AVOIDANCE_WEEK_SPAN consecutive weeks
        weeks_with_miss = self._count_distinct_weeks(
            matching, signal.scheduled_at
        )
        if weeks_with_miss < settings.AVOIDANCE_WEEK_SPAN:
            logger.debug(
                "[PatternService] Not enough week span | weeks=%d < required=%d",
                weeks_with_miss,
                settings.AVOIDANCE_WEEK_SPAN,
            )
            return False, None

        # Persist avoidance pattern via DAO service
        pattern_id = await self._upsert_avoidance_pattern(
            signal, target_day, target_hour, miss_count, weeks_with_miss
        )
        return True, pattern_id

    @staticmethod
    def _count_distinct_weeks(
        tasks: List[Dict[str, Any]], current_dt: datetime
    ) -> int:
        """Return the number of distinct ISO-week numbers with at least one miss."""
        weeks = set()
        for t in tasks:
            raw = t.get("scheduled_at")
            if raw:
                try:
                    dt = datetime.fromisoformat(str(raw))
                    weeks.add(dt.isocalendar()[1])  # ISO week number
                except ValueError:
                    pass
        weeks.add(current_dt.isocalendar()[1])
        return len(weeks)

    async def _upsert_avoidance_pattern(
        self,
        signal: TaskMissSignal,
        day: str,
        hour: int,
        miss_count: int,
        week_span: int,
    ) -> Optional[UUID]:
        """Create or update an avoidance Pattern record via the DAO service."""
        confidence = min(0.95, 0.5 + (miss_count - settings.AVOIDANCE_MISS_THRESHOLD) * 0.1)
        time_range = f"{hour:02d}:00-{hour + 1:02d}:00"
        pattern_data = {
            "day": day,
            "time_range": time_range,
            "reason": (
                f"{miss_count} misses detected in slot {day} {time_range} "
                f"across {week_span} consecutive weeks."
            ),
            "confidence": round(confidence, 2),
            "miss_count": miss_count,
            "category": signal.category,
            "last_miss_task_id": str(signal.task_id),
        }

        logger.info(
            "[PatternService] Upserting avoidance pattern | user=%s | day=%s | hour=%d | confidence=%.2f",
            signal.user_id,
            day,
            hour,
            confidence,
        )

        payload = {
            "user_id": str(signal.user_id),
            "pattern_type": "avoidance",
            "description": (
                f"User consistently misses tasks on {day} between "
                f"{time_range}. Detected over {week_span} consecutive weeks."
            ),
            "data": pattern_data,
            "confidence": round(confidence, 2),
        }

        try:
            resp = await self._client().post("/patterns", json=payload)
            resp.raise_for_status()
            result = resp.json()
            pattern_id = UUID(result.get("id", "")) if result.get("id") else None
            logger.info(
                "[PatternService] Pattern upserted | pattern_id=%s", pattern_id
            )
            return pattern_id
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[PatternService] DAO pattern upsert failed | status=%d | body=%s",
                exc.response.status_code,
                exc.response.text[:200],
                exc_info=True,
            )
        except Exception as exc:
            logger.error(
                "[PatternService] DAO pattern upsert error | error=%s",
                exc,
                exc_info=True,
            )
        return None

    # ------------------------------------------------------------------
    # DAO service calls
    # ------------------------------------------------------------------

    async def _fetch_task_history(
        self,
        user_id: UUID,
        lookback_days: int,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve task history from the DAO service."""
        since = (
            datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
        ).isoformat()

        params: Dict[str, Any] = {
            "user_id": str(user_id),
            "since": since,
        }
        if status_filter:
            params["status"] = status_filter

        logger.debug(
            "[PatternService] Fetching task history | user=%s | since=%s | status=%s",
            user_id,
            since,
            status_filter,
        )

        try:
            resp = await self._client().get("/tasks", params=params)
            resp.raise_for_status()
            data = resp.json()
            tasks = data if isinstance(data, list) else data.get("items", [])
            logger.debug(
                "[PatternService] Task history fetched | count=%d", len(tasks)
            )
            return self._enrich_tasks(tasks)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "[PatternService] DAO task fetch failed | status=%d | body=%s",
                exc.response.status_code,
                exc.response.text[:200],
                exc_info=True,
            )
            return []
        except Exception as exc:
            logger.error(
                "[PatternService] DAO task fetch error | error=%s",
                exc,
                exc_info=True,
            )
            return []

    @staticmethod
    def _enrich_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Annotate tasks with day_of_week and hour derived from scheduled_at."""
        enriched = []
        for t in tasks:
            raw = t.get("scheduled_at")
            if raw:
                try:
                    dt = datetime.fromisoformat(str(raw))
                    t["day_of_week"] = dt.strftime("%A")
                    t["hour"] = dt.hour
                except ValueError:
                    pass
            enriched.append(t)
        return enriched
