"""SQLAlchemy implementation of PatternDAOProtocol."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.pattern_model import Pattern
from dao_service.schemas.pattern import PatternCreateDTO, PatternDTO, PatternUpdateDTO


class DaoPattern:
    async def create(self, db: DatabaseSession, obj_in: PatternCreateDTO) -> PatternDTO:
        session: SQLAlchemyAsyncSession = db
        db_obj = Pattern(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return PatternDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[PatternDTO]:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(Pattern).where(Pattern.id == id))
        db_obj = result.scalar_one_or_none()
        return PatternDTO.model_validate(db_obj) if db_obj else None

    async def get_multi(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[PatternDTO]:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(
            select(Pattern).offset(skip).limit(limit).order_by(Pattern.updated_at.desc())
        )
        return [PatternDTO.model_validate(row) for row in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(func.count(Pattern.id)))
        return result.scalar_one()

    async def update(self, db: DatabaseSession, id: UUID, obj_in: PatternUpdateDTO) -> Optional[PatternDTO]:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(Pattern).where(Pattern.id == id))
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return PatternDTO.model_validate(db_obj)

    async def delete(self, db: DatabaseSession, id: UUID) -> bool:
        session: SQLAlchemyAsyncSession = db
        result = await session.execute(select(Pattern).where(Pattern.id == id))
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return False
        await session.delete(db_obj)
        await session.flush()
        return True
