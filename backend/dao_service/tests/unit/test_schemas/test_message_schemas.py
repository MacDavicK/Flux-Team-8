"""Unit tests for Message DTO validation."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.message import MessageCreateDTO, MessageDTO, MessageUpdateDTO


class TestMessageCreateDTO:
    def test_valid_message_minimal(self):
        dto = MessageCreateDTO(
            conversation_id=uuid4(), role="user", content="Hello"
        )
        assert dto.role == "user"
        assert dto.input_modality == "text"
        assert dto.metadata == {}

    def test_valid_message_with_voice_modality(self):
        dto = MessageCreateDTO(
            conversation_id=uuid4(), role="assistant", content="Hi there",
            input_modality="voice",
        )
        assert dto.input_modality == "voice"

    def test_invalid_role_raises_error(self):
        with pytest.raises(ValidationError):
            MessageCreateDTO(
                conversation_id=uuid4(), role="admin", content="Hello"
            )

    def test_invalid_modality_raises_error(self):
        with pytest.raises(ValidationError):
            MessageCreateDTO(
                conversation_id=uuid4(), role="user", content="Hello",
                input_modality="video",
            )

    def test_empty_content_raises_error(self):
        with pytest.raises(ValidationError):
            MessageCreateDTO(
                conversation_id=uuid4(), role="user", content=""
            )

    def test_all_valid_roles(self):
        for role in ("user", "assistant", "system", "function"):
            dto = MessageCreateDTO(
                conversation_id=uuid4(), role=role, content="test"
            )
            assert dto.role == role


class TestMessageUpdateDTO:
    def test_empty_update_allowed(self):
        dto = MessageUpdateDTO()
        assert dto.role is None
        assert dto.content is None

    def test_partial_update_role(self):
        dto = MessageUpdateDTO(role="assistant")
        assert dto.role == "assistant"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            MessageUpdateDTO(role="admin")


class TestMessageDTO:
    def test_from_attributes(self):
        now = datetime.now(timezone.utc)
        msg_id = uuid4()
        conv_id = uuid4()
        dto = MessageDTO.model_validate({
            "id": msg_id,
            "conversation_id": conv_id,
            "role": "user",
            "content": "Test message",
            "input_modality": "text",
            "metadata": {},
            "created_at": now,
        })
        assert dto.id == msg_id
        assert dto.conversation_id == conv_id
        assert dto.role == "user"
        assert dto.created_at == now
