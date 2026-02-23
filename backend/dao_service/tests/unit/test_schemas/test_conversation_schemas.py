"""Unit tests for Conversation DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.conversation import ConversationCreateDTO, ConversationUpdateDTO


class TestConversationCreateDTO:
    def test_valid_conversation(self):
        dto = ConversationCreateDTO(
            user_id=uuid4(),
            langgraph_thread_id="thread-123",
            context_type="goal",
        )
        assert dto.context_type == "goal"

    def test_all_context_types_allowed(self):
        for context_type in ["onboarding", "goal", "task", "reschedule"]:
            dto = ConversationCreateDTO(
                user_id=uuid4(),
                langgraph_thread_id=f"thread-{context_type}",
                context_type=context_type,
            )
            assert dto.context_type == context_type

    def test_invalid_context_type_rejected(self):
        with pytest.raises(ValidationError):
            ConversationCreateDTO(
                user_id=uuid4(),
                langgraph_thread_id="thread-abc",
                context_type="chat",
            )

    def test_empty_thread_id_rejected(self):
        with pytest.raises(ValidationError):
            ConversationCreateDTO(user_id=uuid4(), langgraph_thread_id="", context_type="goal")


class TestConversationUpdateDTO:
    def test_empty_update_allowed(self):
        dto = ConversationUpdateDTO()
        assert dto.context_type is None

    def test_valid_context_update(self):
        dto = ConversationUpdateDTO(context_type="task")
        assert dto.context_type == "task"

    def test_invalid_context_update_rejected(self):
        with pytest.raises(ValidationError):
            ConversationUpdateDTO(context_type="invalid")
