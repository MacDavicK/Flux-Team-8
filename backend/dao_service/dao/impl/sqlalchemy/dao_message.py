"""SQLAlchemy DAO implementation for Message."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.message_model import Message
from dao_service.schemas.message import MessageCreateDTO, MessageDTO


class DaoMessage:
    """SQLAlchemy-specific message DAO."""

    async def create(self, db: DatabaseSession, obj_in: MessageCreateDTO) -> MessageDTO:
        """Insert a new message row."""
        session: SQLAlchemyAsyncSession = db
        data = obj_in.model_dump()
        # Map DTO 'metadata' field to ORM 'metadata_' attribute
        data["metadata_"] = data.pop("metadata", {})
        db_obj = Message(**data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return MessageDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[MessageDTO]:
        """Fetch a single message by primary key."""
        session: SQLAlchemyAsyncSession = db
        stmt = select(Message).where(Message.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return MessageDTO.model_validate(db_obj) if db_obj else None

    async def get_by_conversation(
        self, db: DatabaseSession, conversation_id: UUID, skip: int = 0, limit: int = 500
    ) -> List[MessageDTO]:
        """Fetch messages for a conversation, ordered chronologically."""
        session: SQLAlchemyAsyncSession = db
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return [MessageDTO.model_validate(r) for r in result.scalars().all()]

    async def get_multi(self, db: DatabaseSession, skip: int = 0, limit: int = 100) -> List[MessageDTO]:
        """Fetch messages with pagination."""
        session: SQLAlchemyAsyncSession = db
        stmt = select(Message).offset(skip).limit(limit).order_by(Message.created_at.desc())
        result = await session.execute(stmt)
        return [MessageDTO.model_validate(r) for r in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        """Count all messages."""
        session: SQLAlchemyAsyncSession = db
        stmt = select(func.count(Message.id))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def count_by_conversation(self, db: DatabaseSession, conversation_id: UUID) -> int:
        """Count messages for a specific conversation."""
        session: SQLAlchemyAsyncSession = db
        stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        result = await session.execute(stmt)
        return result.scalar_one()

    async def delete(self, db: DatabaseSession, id: UUID) -> bool:
        """Delete a message by primary key."""
        session: SQLAlchemyAsyncSession = db
        stmt = select(Message).where(Message.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return False
        await session.delete(db_obj)
        await session.flush()
        return True
