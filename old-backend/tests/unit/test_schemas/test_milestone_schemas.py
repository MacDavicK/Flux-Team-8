"""Unit tests for Milestone DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.milestone import MilestoneCreateDTO, MilestoneUpdateDTO


class TestMilestoneCreateDTO:
    def test_valid_milestone(self):
        dto = MilestoneCreateDTO(goal_id=uuid4(), week_number=1, title="Week 1 tasks")
        assert dto.status == "pending"

    def test_week_number_zero_rejected(self):
        with pytest.raises(ValidationError):
            MilestoneCreateDTO(goal_id=uuid4(), week_number=0, title="Week 0")

    def test_negative_week_number_rejected(self):
        with pytest.raises(ValidationError):
            MilestoneCreateDTO(goal_id=uuid4(), week_number=-1, title="Negative week")

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            MilestoneCreateDTO(goal_id=uuid4(), week_number=1, title="")

    def test_missing_goal_id_rejected(self):
        with pytest.raises(ValidationError):
            MilestoneCreateDTO(week_number=1, title="No goal")


class TestMilestoneUpdateDTO:
    def test_empty_update_allowed(self):
        dto = MilestoneUpdateDTO()
        assert dto.week_number is None

    def test_status_update(self):
        dto = MilestoneUpdateDTO(status="completed")
        assert dto.status == "completed"

    def test_zero_week_rejected(self):
        with pytest.raises(ValidationError):
            MilestoneUpdateDTO(week_number=0)
