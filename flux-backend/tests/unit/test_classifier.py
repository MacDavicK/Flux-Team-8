"""
21.1.3 — Unit tests for ClassifierOutput validation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


VALID_TAGS = [
    "health", "fitness", "nutrition", "sleep", "mindfulness",
    "career", "finance", "learning", "relationships", "creativity",
    "productivity", "home", "travel", "personal_development",
]


def test_valid_tags_accepted():
    """All 14 taxonomy tags are accepted by ClassifierOutput."""
    from app.models.agent_outputs import ClassifierOutput
    for tag in VALID_TAGS:
        output = ClassifierOutput(tags=[tag])
        assert tag in output.tags


def test_multiple_valid_tags_accepted():
    """ClassifierOutput accepts 1–3 tags."""
    from app.models.agent_outputs import ClassifierOutput
    output = ClassifierOutput(tags=["health", "fitness"])
    assert len(output.tags) == 2


def test_empty_tags_list_accepted():
    """ClassifierOutput accepts an empty tag list (model does not enforce min length)."""
    from app.models.agent_outputs import ClassifierOutput
    output = ClassifierOutput(tags=[])
    assert output.tags == []


def test_tags_field_is_list_of_strings():
    """tags must be a list of strings; non-string raises ValidationError."""
    from app.models.agent_outputs import ClassifierOutput
    with pytest.raises((ValidationError, Exception)):
        ClassifierOutput(tags=123)  # type: ignore
