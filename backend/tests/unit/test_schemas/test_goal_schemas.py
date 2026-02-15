"""Unit tests for Goal DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.goal import GoalCreateDTO, GoalStructureCreateDTO, GoalUpdateDTO


class TestGoalCreateDTO:
    def test_valid_goal(self):
        dto = GoalCreateDTO(user_id=uuid4(), title="Run a marathon")
        assert dto.status == "active"
        assert dto.category is None

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            GoalCreateDTO(user_id=uuid4(), title="")

    def test_title_max_length(self):
        with pytest.raises(ValidationError):
            GoalCreateDTO(user_id=uuid4(), title="x" * 501)


class TestGoalStructureCreateDTO:
    def test_valid_structure(self):
        dto = GoalStructureCreateDTO(
            goal=GoalCreateDTO(user_id=uuid4(), title="Fitness plan"),
            milestones=[
                {
                    "week_number": 1,
                    "title": "Week 1",
                    "tasks": [{"title": "Run 2km"}, {"title": "Stretch"}],
                },
                {
                    "week_number": 2,
                    "title": "Week 2",
                    "tasks": [{"title": "Run 5km"}],
                },
            ],
        )
        assert len(dto.milestones) == 2
        assert len(dto.milestones[0].tasks) == 2

    def test_empty_milestones_allowed(self):
        dto = GoalStructureCreateDTO(
            goal=GoalCreateDTO(user_id=uuid4(), title="Minimal goal"),
        )
        assert dto.milestones == []


class TestGoalUpdateDTO:
    def test_empty_update_allowed(self):
        dto = GoalUpdateDTO()
        assert dto.title is None

    def test_partial_update(self):
        dto = GoalUpdateDTO(status="completed")
        assert dto.status == "completed"
