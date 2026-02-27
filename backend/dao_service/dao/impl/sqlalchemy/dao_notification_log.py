"""SQLAlchemy implementation of NotificationLogDAOProtocol."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.notification_log_model import NotificationLog
from dao_service.schemas.notification_log import (
    NotificationLogCreateDTO,
    NotificationLogDTO,
    NotificationLogUpdateDTO,
)


class DaoNotificationLog:
    async def create(self, db: DatabaseSession, obj_in: NotificationLogCreateDTO) -> NotificationLogDTO:
        session: SQLAlchemyAsyncSession = db
        db_obj = NotificationLog(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return NotificationLogDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[NotificationLogDTO]:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(NotificationLog).where(NotificationLog.id == id))
        db_obj = result.scalar_one_or_none()
        return NotificationLogDTO.model_validate(db_obj) if db_obj else None

    async def get_multi(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[NotificationLogDTO]:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(
            select(NotificationLog).offset(skip).limit(limit).order_by(NotificationLog.sent_at.desc())
        )
        return [NotificationLogDTO.model_validate(row) for row in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(func.count(NotificationLog.id)))
        return result.scalar_one()

    async def update(
        self, db: DatabaseSession, id: UUID, obj_in: NotificationLogUpdateDTO
    ) -> Optional[NotificationLogDTO]:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(NotificationLog).where(NotificationLog.id == id))
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return NotificationLogDTO.model_validate(db_obj)

    async def delete(self, db: DatabaseSession, id: UUID) -> bool:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(NotificationLog).where(NotificationLog.id == id))
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return False
        await session.delete(db_obj)
        await session.flush()
        return True
