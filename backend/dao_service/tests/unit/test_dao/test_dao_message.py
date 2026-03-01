"""
Unit tests for DaoMessage SQLAlchemy implementation.

All database interactions are replaced with AsyncMock -- no real database required.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from dao_service.dao.impl.sqlalchemy.dao_message import DaoMessage
from dao_service.models.message_model import Message
from dao_service.schemas.message import MessageCreateDTO, MessageDTO


# -- Helpers -----------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_session():
    """AsyncMock that behaves like an AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _result_scalar_one_or_none(obj):
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    return result


def _result_scalar_one(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _result_scalars_all(items):
    scalars = MagicMock()
    scalars.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _make_message(**kw) -> Message:
    msg = Message(
        id=kw.get("id", uuid4()),
        conversation_id=kw.get("conversation_id", uuid4()),
        role=kw.get("role", "user"),
        content=kw.get("content", "Test message"),
        input_modality=kw.get("input_modality", "text"),
        created_at=kw.get("created_at", _now()),
    )
    # Set the column-aliased attribute directly to avoid MetaData conflict
    msg.metadata_ = kw.get("metadata_", {})
    return msg


# -- Tests -------------------------------------------------------------------


@pytest.mark.asyncio
class TestDaoMessage:
    async def test_create_calls_add_flush_refresh(self):
        dao = DaoMessage()
        db = _mock_session()
        conv_id = uuid4()

        async def populate(obj):
            obj.id = uuid4()
            obj.created_at = _now()

        db.refresh = AsyncMock(side_effect=populate)

        result = await dao.create(
            db,
            MessageCreateDTO(conversation_id=conv_id, role="user", content="Hi"),
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        db.refresh.assert_called_once()
        assert result.role == "user"
        assert result.content == "Hi"

    async def test_get_by_id_found(self):
        dao = DaoMessage()
        db = _mock_session()
        msg = _make_message()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(msg))

        result = await dao.get_by_id(db, msg.id)

        assert result is not None
        assert result.id == msg.id

    async def test_get_by_id_not_found(self):
        dao = DaoMessage()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        result = await dao.get_by_id(db, uuid4())

        assert result is None

    async def test_get_by_conversation_returns_list(self):
        dao = DaoMessage()
        db = _mock_session()
        conv_id = uuid4()
        msgs = [_make_message(conversation_id=conv_id) for _ in range(3)]
        db.execute = AsyncMock(return_value=_result_scalars_all(msgs))

        result = await dao.get_by_conversation(db, conv_id)

        assert len(result) == 3

    async def test_count_returns_integer(self):
        dao = DaoMessage()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one(5))

        assert await dao.count(db) == 5

    async def test_count_by_conversation(self):
        dao = DaoMessage()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one(3))

        assert await dao.count_by_conversation(db, uuid4()) == 3

    async def test_delete_found_returns_true(self):
        dao = DaoMessage()
        db = _mock_session()
        msg = _make_message()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(msg))

        assert await dao.delete(db, msg.id) is True
        db.delete.assert_called_once_with(msg)
        db.flush.assert_called_once()

    async def test_delete_not_found_returns_false(self):
        dao = DaoMessage()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.delete(db, uuid4()) is False
        db.delete.assert_not_called()
