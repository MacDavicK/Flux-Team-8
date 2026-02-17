"""SQLAlchemy implementation of UserDAOProtocol."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.user_model import User
from dao_service.schemas.user import UserCreateDTO, UserDTO, UserUpdateDTO


class DaoUser:
    """SQLAlchemy-specific user DAO."""

    async def create(self, db: DatabaseSession, obj_in: UserCreateDTO) -> UserDTO:
        session: SQLAlchemyAsyncSession = db
        db_obj = User(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return UserDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[UserDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(User).where(User.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return UserDTO.model_validate(db_obj) if db_obj else None

    async def get_multi(self, db: DatabaseSession, skip: int = 0, limit: int = 100) -> List[UserDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await session.execute(stmt)
        return [UserDTO.model_validate(r) for r in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        session: SQLAlchemyAsyncSession = db
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def update(self, db: DatabaseSession, id: UUID, obj_in: UserUpdateDTO) -> Optional[UserDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(User).where(User.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return UserDTO.model_validate(db_obj)

    async def delete(self, db: DatabaseSession, id: UUID) -> bool:
        session: SQLAlchemyAsyncSession = db
        stmt = select(User).where(User.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return False
        await session.delete(db_obj)
        await session.flush()
        return True
