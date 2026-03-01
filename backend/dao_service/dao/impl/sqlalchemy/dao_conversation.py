"""SQLAlchemy implementation of ConversationDAOProtocol."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.conversation_model import Conversation
from dao_service.schemas.conversation import (
    ConversationCreateDTO,
    ConversationDTO,
    ConversationUpdateDTO,
    VoiceConversationUpdateDTO,
)


class DaoConversation:
    """SQLAlchemy-specific conversation DAO."""

    async def create(self, db: DatabaseSession, obj_in: ConversationCreateDTO) -> ConversationDTO:
        session: SQLAlchemyAsyncSession = db
        db_obj = Conversation(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return ConversationDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[ConversationDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Conversation).where(Conversation.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return ConversationDTO.model_validate(db_obj) if db_obj else None

    async def get_multi(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[ConversationDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = (
            select(Conversation)
            .offset(skip)
            .limit(limit)
            .order_by(Conversation.created_at.desc())
        )
        result = await session.execute(stmt)
        return [ConversationDTO.model_validate(r) for r in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        session: SQLAlchemyAsyncSession = db
        stmt = select(func.count(Conversation.id))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def update(
        self, db: DatabaseSession, id: UUID, obj_in: ConversationUpdateDTO
    ) -> Optional[ConversationDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Conversation).where(Conversation.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return ConversationDTO.model_validate(db_obj)

    async def update_voice_fields(
        self, db: DatabaseSession, id: UUID, obj_in: VoiceConversationUpdateDTO
    ) -> Optional[ConversationDTO]:
        """Update only voice-specific fields on a conversation."""
        session: SQLAlchemyAsyncSession = db
        stmt = select(Conversation).where(Conversation.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return ConversationDTO.model_validate(db_obj)
