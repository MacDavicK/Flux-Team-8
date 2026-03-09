"""
Unit tests for DaoMessageService.

DAO dependency is replaced with MagicMock/AsyncMock -- no real database required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from dao_service.schemas.message import MessageCreateDTO, MessageDTO
from dao_service.services.dao_message_service import DaoMessageService


# -- Helpers -----------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_db():
    return AsyncMock()


def _make_message_dto(**kw) -> MessageDTO:
    return MessageDTO(
        id=kw.get("id", uuid4()),
        conversation_id=kw.get("conversation_id", uuid4()),
        role=kw.get("role", "user"),
        content=kw.get("content", "Test"),
        input_modality=kw.get("input_modality", "text"),
        metadata=kw.get("metadata", {}),
        created_at=kw.get("created_at", _now()),
    )


def _message_service(mock_dao) -> DaoMessageService:
    """Bypass __init__ to inject mock DAO."""
    svc = DaoMessageService.__new__(DaoMessageService)
    svc.message_dao = mock_dao
    return svc


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
class TestDaoMessageService:
    async def test_create_message_delegates_to_dao(self):
        mock_dao = MagicMock()
        conv_id = uuid4()
        expected = _make_message_dto(conversation_id=conv_id, content="Hello")
        mock_dao.create = AsyncMock(return_value=expected)
        svc = _message_service(mock_dao)

        result = await svc.create_message(
            _mock_db(),
            MessageCreateDTO(conversation_id=conv_id, role="user", content="Hello"),
        )

        assert result.content == "Hello"
        mock_dao.create.assert_called_once()

    async def test_get_messages_for_conversation(self):
        mock_dao = MagicMock()
        expected = [_make_message_dto(), _make_message_dto()]
        mock_dao.get_by_conversation = AsyncMock(return_value=expected)
        svc = _message_service(mock_dao)

        result = await svc.get_messages_for_conversation(_mock_db(), uuid4())

        assert len(result) == 2
        mock_dao.get_by_conversation.assert_called_once()

    async def test_get_message_returns_none_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id = AsyncMock(return_value=None)
        svc = _message_service(mock_dao)

        assert await svc.get_message(_mock_db(), uuid4()) is None

    async def test_delete_message_returns_true(self):
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=True)
        svc = _message_service(mock_dao)

        assert await svc.delete_message(_mock_db(), uuid4()) is True

    async def test_delete_message_returns_false_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=False)
        svc = _message_service(mock_dao)

        assert await svc.delete_message(_mock_db(), uuid4()) is False

    async def test_count_messages_for_conversation(self):
        mock_dao = MagicMock()
        mock_dao.count_by_conversation = AsyncMock(return_value=7)
        svc = _message_service(mock_dao)

        assert await svc.count_messages_for_conversation(_mock_db(), uuid4()) == 7
