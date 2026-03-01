"""Unit tests for Pattern DTO validation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.pattern import PatternCreateDTO, PatternDTO, PatternUpdateDTO


class TestPatternCreateDTO:
    def test_valid_pattern(self):
        dto = PatternCreateDTO(user_id=uuid4(), pattern_type="completion_streak", confidence=0.8)
        assert dto.confidence == 0.8

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            PatternCreateDTO(user_id=uuid4(), confidence=1.1)
        with pytest.raises(ValidationError):
            PatternCreateDTO(user_id=uuid4(), confidence=-0.1)


class TestPatternUpdateDTO:
    def test_empty_update_allowed(self):
        dto = PatternUpdateDTO()
        assert dto.pattern_type is None

    def test_confidence_bounds(self):
        dto_low = PatternUpdateDTO(confidence=0.0)
        dto_high = PatternUpdateDTO(confidence=1.0)
        assert dto_low.confidence == 0.0
        assert dto_high.confidence == 1.0


class TestPatternDTO:
    def test_valid_dto(self):
        now = datetime.now(timezone.utc)
        dto = PatternDTO(
            id=uuid4(),
            user_id=uuid4(),
            pattern_type="time_avoidance",
            description="Avoids mornings",
            data={"hour": 8},
            confidence=0.6,
            created_at=now,
            updated_at=now,
        )
        assert dto.pattern_type == "time_avoidance"
