"""Unit tests for the Pattern Observer Agent (SCRUM-50).

Run with: pytest test_pattern_observer.py -v
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from models import (
    AvoidSlot,
    CategoryPerformance,
    ConsultationRequest,
    MissSignalResponse,
    PatternSummary,
    TaskMissSignal,
)
from pattern_analyzer import PatternAnalyzer
from pattern_service import PatternService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    status: str = "completed",
    day_of_week: str = "Monday",
    hour: int = 8,
    weeks_ago: int = 0,
    category: str = "Fitness",
) -> dict:
    dt = datetime.now(tz=timezone.utc) - timedelta(weeks=weeks_ago, hours=0)
    # Adjust to correct day
    return {
        "id": str(uuid4()),
        "status": status,
        "scheduled_at": dt.isoformat(),
        "completed_at": dt.isoformat() if status == "completed" else None,
        "category": category,
        "day_of_week": day_of_week,
        "hour": hour,
    }


# ---------------------------------------------------------------------------
# PatternAnalyzer unit tests
# ---------------------------------------------------------------------------

class TestPatternAnalyzer:
    def setup_method(self):
        self.analyzer = PatternAnalyzer()

    def test_cold_start_no_tasks(self):
        """Returns cold-start summary when task list is empty."""
        summary = self.analyzer._cold_start_summary()
        assert summary.low_confidence is True
        assert len(summary.best_times) > 0

    def test_is_low_confidence_empty(self):
        assert self.analyzer._is_low_confidence([]) is True

    def test_is_low_confidence_short_span(self):
        """Single-day history is always low-confidence."""
        tasks = [_make_task(weeks_ago=0), _make_task(weeks_ago=0)]
        assert self.analyzer._is_low_confidence(tasks) is True

    def test_is_low_confidence_sufficient_span(self):
        """3-week span should pass the threshold."""
        tasks = [_make_task(weeks_ago=3), _make_task(weeks_ago=0)]
        assert self.analyzer._is_low_confidence(tasks) is False

    def test_parse_llm_response_valid(self):
        raw = json.dumps({
            "best_times": ["07:00-09:00"],
            "avoid_slots": [
                {"day": "Monday", "time_range": "07:00-09:00",
                 "reason": "3 consecutive misses", "confidence": 0.85}
            ],
            "category_performance": [
                {"category": "Fitness", "completion_rate": 0.78}
            ],
            "general_notes": "User performs best in the morning.",
        })
        summary = self.analyzer._parse_llm_response(raw)
        assert summary.best_times == ["07:00-09:00"]
        assert summary.avoid_slots[0].day == "Monday"
        assert summary.category_performance[0].completion_rate == 0.78

    def test_parse_llm_response_malformed(self):
        """Malformed LLM output should return an empty PatternSummary, not raise."""
        summary = self.analyzer._parse_llm_response("NOT JSON{{{")
        assert isinstance(summary, PatternSummary)
        assert summary.best_times == []

    def test_build_user_prompt_contains_tasks(self):
        tasks = [_make_task(), _make_task(status="missed")]
        prompt = self.analyzer._build_user_prompt(tasks)
        assert "task history" in prompt.lower()
        assert "completed" in prompt or "missed" in prompt


# ---------------------------------------------------------------------------
# PatternService unit tests
# ---------------------------------------------------------------------------

class TestPatternService:
    def setup_method(self):
        self.service = PatternService()

    def test_enrich_tasks_adds_day_and_hour(self):
        tasks = [{"scheduled_at": "2025-10-06T08:30:00"}]  # Monday
        enriched = PatternService._enrich_tasks(tasks)
        assert enriched[0]["day_of_week"] == "Monday"
        assert enriched[0]["hour"] == 8

    def test_enrich_tasks_skips_invalid_dates(self):
        tasks = [{"scheduled_at": "not-a-date"}]
        enriched = PatternService._enrich_tasks(tasks)
        assert "day_of_week" not in enriched[0]

    def test_count_distinct_weeks(self):
        now = datetime(2025, 10, 6, 8, 0, tzinfo=timezone.utc)
        tasks = [
            {"scheduled_at": "2025-09-22T08:00:00"},  # week 39
            {"scheduled_at": "2025-09-29T08:00:00"},  # week 40
        ]
        count = PatternService._count_distinct_weeks(tasks, now)
        assert count == 3  # weeks 39, 40, 41 (current)

    @pytest.mark.asyncio
    async def test_handle_miss_signal_insufficient_history(self):
        """When fewer than AVOIDANCE_MISS_THRESHOLD prior misses exist, no pattern is flagged."""
        signal = TaskMissSignal(
            task_id=uuid4(),
            user_id=uuid4(),
            scheduled_at=datetime.now(tz=timezone.utc),
            category="Fitness",
        )
        # Patch _fetch_task_history to return only 1 prior miss
        with patch.object(
            self.service,
            "_fetch_task_history",
            new=AsyncMock(return_value=[_make_task(status="missed", weeks_ago=1)]),
        ):
            result = await self.service.handle_miss_signal(signal)

        assert isinstance(result, MissSignalResponse)
        assert result.avoidance_flagged is False
        assert result.pattern_id is None

    @pytest.mark.asyncio
    async def test_consult_cold_start(self):
        """Consultation with no task history returns cold-start summary."""
        request = ConsultationRequest(user_id=uuid4())
        with patch.object(
            self.service,
            "_fetch_task_history",
            new=AsyncMock(return_value=[]),
        ):
            result = await self.service.consult(request)

        assert result.data_points_analysed == 0
        assert result.pattern_summary.low_confidence is True
