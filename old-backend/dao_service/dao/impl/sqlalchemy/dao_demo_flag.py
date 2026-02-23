"""SQLAlchemy implementation of DemoFlagDAOProtocol."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.demo_flag_model import DemoFlag
from dao_service.schemas.demo_flag import DemoFlagCreateDTO, DemoFlagDTO


class DaoDemoFlag:
    """SQLAlchemy-specific demo flag DAO."""

    async def get_by_user_id(self, db: DatabaseSession, user_id: UUID) -> Optional[DemoFlagDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(DemoFlag).where(DemoFlag.user_id == user_id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return DemoFlagDTO.model_validate(db_obj) if db_obj else None

    async def upsert(self, db: DatabaseSession, obj_in: DemoFlagCreateDTO) -> DemoFlagDTO:
        session: SQLAlchemyAsyncSession = db
        stmt = select(DemoFlag).where(DemoFlag.user_id == obj_in.user_id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()

        if db_obj is None:
            db_obj = DemoFlag(**obj_in.model_dump())
            session.add(db_obj)
        else:
            update_data = obj_in.model_dump(exclude={"user_id"})
            for field, value in update_data.items():
                setattr(db_obj, field, value)

        await session.flush()
        await session.refresh(db_obj)
        return DemoFlagDTO.model_validate(db_obj)
