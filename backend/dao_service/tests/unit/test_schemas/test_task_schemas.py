"""Unit tests for Task DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.task import BulkUpdateStateRequest, TaskCreateDTO, TaskStatisticsDTO, TaskUpdateDTO


class TestTaskCreateDTO:
    def test_valid_task_minimal(self):
        dto = TaskCreateDTO(title="Run 5km", user_id=uuid4())
        assert dto.status == "pending"
        assert dto.trigger_type == "time"
        assert dto.goal_id is None

    def test_title_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="x" * 501, user_id=uuid4())

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="Bad status", user_id=uuid4(), status="queued")

    def test_invalid_trigger_type_rejected(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="Bad trigger", user_id=uuid4(), trigger_type="geo-fence")

    def test_duration_minutes_must_be_positive(self):
        with pytest.raises(ValidationError):
            TaskCreateDTO(title="Bad duration", user_id=uuid4(), duration_minutes=0)


class TestTaskUpdateDTO:
    def test_empty_update_allowed(self):
        dto = TaskUpdateDTO()
        assert dto.title is None

    def test_partial_update(self):
        dto = TaskUpdateDTO(status="done")
        assert dto.status == "done"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            TaskUpdateDTO(status="queued")

    def test_invalid_trigger_type_rejected(self):
        with pytest.raises(ValidationError):
            TaskUpdateDTO(trigger_type="invalid")


class TestBulkUpdateStateRequest:
    def test_valid_bulk_update(self):
        dto = BulkUpdateStateRequest(task_ids=[uuid4(), uuid4()], new_status="rescheduled")
        assert len(dto.task_ids) == 2

    def test_empty_task_ids_rejected(self):
        with pytest.raises(ValidationError):
            BulkUpdateStateRequest(task_ids=[], new_status="done")

    def test_invalid_new_status_rejected(self):
        with pytest.raises(ValidationError):
            BulkUpdateStateRequest(task_ids=[uuid4()], new_status="queued")


class TestTaskStatisticsDTO:
    def test_valid_statistics(self):
        dto = TaskStatisticsDTO(
            user_id=uuid4(),
            total_tasks=3,
            by_status={"done": 2, "pending": 1},
            completion_rate=0.6667,
        )
        assert dto.total_tasks == 3
        assert dto.by_status["done"] == 2

    def test_empty_statistics(self):
        dto = TaskStatisticsDTO(user_id=uuid4(), total_tasks=0, by_status={}, completion_rate=0.0)
        assert dto.total_tasks == 0
        assert dto.by_status == {}
