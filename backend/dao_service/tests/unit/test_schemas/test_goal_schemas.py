"""Unit tests for Goal DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.goal import GoalCreateDTO, GoalUpdateDTO


class TestGoalCreateDTO:
    def test_valid_goal(self):
        dto = GoalCreateDTO(user_id=uuid4(), title="Run a marathon")
        assert dto.status == "active"
        assert dto.target_weeks == 6

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            GoalCreateDTO(user_id=uuid4(), title="")

    def test_title_max_length(self):
        with pytest.raises(ValidationError):
            GoalCreateDTO(user_id=uuid4(), title="x" * 501)

    def test_all_valid_status_values(self):
        for status in ["active", "completed", "abandoned", "pipeline"]:
            dto = GoalCreateDTO(user_id=uuid4(), title="Goal", status=status)
            assert dto.status == status

    def test_target_weeks_must_be_positive(self):
        with pytest.raises(ValidationError):
            GoalCreateDTO(user_id=uuid4(), title="Goal", target_weeks=0)


class TestGoalUpdateDTO:
    def test_empty_update_allowed(self):
        dto = GoalUpdateDTO()
        assert dto.title is None

    def test_partial_update(self):
        dto = GoalUpdateDTO(status="completed")
        assert dto.status == "completed"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            GoalUpdateDTO(status="draft")

    def test_target_weeks_must_be_positive(self):
        with pytest.raises(ValidationError):
            GoalUpdateDTO(target_weeks=0)
