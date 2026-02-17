"""Unit tests for Task DTO validation — including edge and negative cases."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.task import (
    BulkUpdateStateRequest,
    CalendarEventUpdateRequest,
    TaskCreateDTO,
    TaskDTO,
    TaskStatisticsDTO,
    TaskUpdateDTO,
)
from dao_service.schemas.enums import TaskState, TaskPriority, TriggerType


class TestTaskCreateDTO:
    """Tests for task creation validation."""

    def test_valid_task_minimal(self):
        dto = TaskCreateDTO(
            title="Run 5km",
            user_id=uuid4(),
            goal_id=uuid4(),
        )
        assert dto.state == TaskState.SCHEDULED
        assert dto.priority == TaskPriority.STANDARD
        assert dto.trigger_type == TriggerType.TIME
        assert dto.is_recurring is False
        assert dto.milestone_id is None

    def test_valid_task_all_fields(self):
        now = datetime.now(timezone.utc)
        dto = TaskCreateDTO(
            title="Morning Yoga",
            user_id=uuid4(),
            goal_id=uuid4(),
            milestone_id=uuid4(),
            start_time=now,
            end_time=now + timedelta(hours=1),
            state=TaskState.SCHEDULED,
            priority=TaskPriority.MUST_NOT_MISS,
            trigger_type=TriggerType.ON_LEAVING_HOME,
            is_recurring=True,
        )
        assert dto.priority == TaskPriority.MUST_NOT_MISS

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            TaskCreateDTO(title="", user_id=uuid4(), goal_id=uuid4())
        assert "min_length" in str(exc_info.value).lower() or "at least" in str(exc_info.value).lower()

    def test_title_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="x" * 501, user_id=uuid4(), goal_id=uuid4())

    def test_end_time_before_start_time_rejected(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError) as exc_info:
            TaskCreateDTO(
                title="Bad times",
                user_id=uuid4(),
                goal_id=uuid4(),
                start_time=now + timedelta(hours=2),
                end_time=now,
            )
        assert "end_time must be after start_time" in str(exc_info.value)

    def test_end_time_equal_to_start_time_allowed(self):
        """Edge case: zero-duration task should be allowed."""
        now = datetime.now(timezone.utc)
        dto = TaskCreateDTO(
            title="Instant task",
            user_id=uuid4(),
            goal_id=uuid4(),
            start_time=now,
            end_time=now,
        )
        assert dto.start_time == dto.end_time

    def test_missing_user_id_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="No user", goal_id=uuid4())

    def test_missing_goal_id_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="No goal", user_id=uuid4())

    def test_invalid_state_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(
                title="Bad state",
                user_id=uuid4(),
                goal_id=uuid4(),
                state="nonexistent",
            )

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(
                title="Bad priority",
                user_id=uuid4(),
                goal_id=uuid4(),
                priority="ultra-critical",
            )


class TestTaskUpdateDTO:
    """Tests for partial update validation."""

    def test_empty_update_allowed(self):
        """All fields optional — empty update is valid."""
        dto = TaskUpdateDTO()
        assert dto.title is None
        assert dto.state is None

    def test_partial_update_single_field(self):
        dto = TaskUpdateDTO(state=TaskState.COMPLETED)
        assert dto.state == TaskState.COMPLETED
        assert dto.title is None

    def test_calendar_event_id_update(self):
        dto = TaskUpdateDTO(calendar_event_id="gcal_abc123")
        assert dto.calendar_event_id == "gcal_abc123"


class TestBulkUpdateStateRequest:
    """Tests for bulk state update validation."""

    def test_valid_bulk_update(self):
        dto = BulkUpdateStateRequest(
            task_ids=[uuid4(), uuid4(), uuid4()],
            new_state=TaskState.DRIFTED,
        )
        assert len(dto.task_ids) == 3

    def test_empty_task_ids_rejected(self):
        with pytest.raises(ValidationError):
            BulkUpdateStateRequest(task_ids=[], new_state=TaskState.COMPLETED)

    def test_single_task_id_allowed(self):
        dto = BulkUpdateStateRequest(task_ids=[uuid4()], new_state=TaskState.MISSED)
        assert len(dto.task_ids) == 1


class TestCalendarEventUpdateRequest:
    """Tests for calendar event update validation."""

    def test_valid_calendar_event_id(self):
        dto = CalendarEventUpdateRequest(calendar_event_id="gcal_evt_abc123")
        assert dto.calendar_event_id == "gcal_evt_abc123"

    def test_empty_calendar_event_id_rejected(self):
        with pytest.raises(ValidationError):
            CalendarEventUpdateRequest(calendar_event_id="")

    def test_calendar_event_id_max_length(self):
        with pytest.raises(ValidationError):
            CalendarEventUpdateRequest(calendar_event_id="x" * 256)


class TestTaskStatisticsDTO:
    """Tests for statistics response validation."""

    def test_valid_statistics(self):
        dto = TaskStatisticsDTO(
            user_id=uuid4(),
            total_tasks=68,
            by_state={"scheduled": 15, "completed": 42, "drifted": 8, "missed": 3},
            completion_rate=0.6176,
        )
        assert dto.completion_rate == 0.6176
        assert dto.total_tasks == 68

    def test_zero_tasks_statistics(self):
        """Edge case: user with no tasks."""
        dto = TaskStatisticsDTO(
            user_id=uuid4(),
            total_tasks=0,
            by_state={},
            completion_rate=0.0,
        )
        assert dto.total_tasks == 0
        assert dto.completion_rate == 0.0
