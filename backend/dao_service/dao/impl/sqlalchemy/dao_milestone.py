"""SQLAlchemy implementation of MilestoneDAOProtocol."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.milestone_model import Milestone
from dao_service.schemas.milestone import MilestoneCreateDTO, MilestoneDTO, MilestoneUpdateDTO


class DaoMilestone:
    """SQLAlchemy-specific milestone DAO."""

    async def create(self, db: DatabaseSession, obj_in: MilestoneCreateDTO) -> MilestoneDTO:
        session: SQLAlchemyAsyncSession = db
        db_obj = Milestone(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return MilestoneDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[MilestoneDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Milestone).where(Milestone.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return MilestoneDTO.model_validate(db_obj) if db_obj else None

    async def get_multi(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[MilestoneDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Milestone).offset(skip).limit(limit).order_by(Milestone.created_at.desc())
        result = await session.execute(stmt)
        return [MilestoneDTO.model_validate(r) for r in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        session: SQLAlchemyAsyncSession = db
        stmt = select(func.count(Milestone.id))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def update(
        self, db: DatabaseSession, id: UUID, obj_in: MilestoneUpdateDTO
    ) -> Optional[MilestoneDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Milestone).where(Milestone.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return MilestoneDTO.model_validate(db_obj)

    async def delete(self, db: DatabaseSession, id: UUID) -> bool:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Milestone).where(Milestone.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return False
        await session.delete(db_obj)
        await session.flush()
        return True
