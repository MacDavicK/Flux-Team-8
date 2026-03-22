"""Unit tests for ClarifierQuestionSchema.multi_select field."""

from app.models.api_schemas import ClarifierQuestionSchema


def test_multi_select_defaults_to_false():
    q = ClarifierQuestionSchema(id="q1", question="Which days?", options=["Mon", "Tue"])
    assert q.multi_select is False


def test_multi_select_can_be_set_to_true():
    q = ClarifierQuestionSchema(
        id="q1", question="Which days?", options=["Mon", "Tue"], multi_select=True
    )
    assert q.multi_select is True


def test_multi_select_false_question_unchanged():
    """Existing questions without multi_select still parse correctly."""
    data = {"id": "q1", "question": "Fitness level?", "options": ["Beginner"]}
    q = ClarifierQuestionSchema(**data)
    assert q.multi_select is False
