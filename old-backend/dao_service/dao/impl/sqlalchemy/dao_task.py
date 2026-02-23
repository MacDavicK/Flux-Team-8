"""SQLAlchemy implementation of TaskDAOProtocol with Scheduler/Observer custom queries."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from dao_service.core.database import DatabaseSession
from dao_service.models.enums import TaskStateEnum
from dao_service.models.task_model import Task
from dao_service.schemas.enums import TaskState
from dao_service.schemas.task import TaskCreateDTO, TaskDTO, TaskUpdateDTO


class DaoTask:
    """SQLAlchemy implementation of TaskDAOProtocol."""

    async def create(self, db: DatabaseSession, obj_in: TaskCreateDTO) -> TaskDTO:
        session: SQLAlchemyAsyncSession = db
        db_obj = Task(**obj_in.model_dump())
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return TaskDTO.model_validate(db_obj)

    async def get_by_id(self, db: DatabaseSession, id: UUID) -> Optional[TaskDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Task).where(Task.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        return TaskDTO.model_validate(db_obj) if db_obj else None

    async def get_multi(self, db: DatabaseSession, skip: int = 0, limit: int = 100) -> List[TaskDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Task).offset(skip).limit(limit).order_by(Task.created_at.desc())
        result = await session.execute(stmt)
        return [TaskDTO.model_validate(r) for r in result.scalars().all()]

    async def count(self, db: DatabaseSession) -> int:
        session: SQLAlchemyAsyncSession = db
        stmt = select(func.count(Task.id))
        result = await session.execute(stmt)
        return result.scalar_one()

    async def update(self, db: DatabaseSession, id: UUID, obj_in: TaskUpdateDTO) -> Optional[TaskDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Task).where(Task.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await session.flush()
        await session.refresh(db_obj)
        return TaskDTO.model_validate(db_obj)

    async def delete(self, db: DatabaseSession, id: UUID) -> bool:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Task).where(Task.id == id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return False
        await session.delete(db_obj)
        await session.flush()
        return True

    # --- Custom methods for Scheduler ---

    async def get_tasks_by_user_and_timerange(
        self, db: DatabaseSession, user_id: UUID, start_time: datetime, end_time: datetime
    ) -> List[TaskDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.start_time >= start_time)
            .where(Task.start_time <= end_time)
            .order_by(Task.start_time)
        )
        result = await session.execute(stmt)
        return [TaskDTO.model_validate(t) for t in result.scalars().all()]

    async def update_calendar_event_id(
        self, db: DatabaseSession, task_id: UUID, calendar_event_id: str
    ) -> Optional[TaskDTO]:
        session: SQLAlchemyAsyncSession = db
        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None
        db_obj.calendar_event_id = calendar_event_id
        await session.flush()
        await session.refresh(db_obj)
        return TaskDTO.model_validate(db_obj)

    async def bulk_update_state(
        self, db: DatabaseSession, task_ids: List[UUID], new_state: TaskState
    ) -> int:
        session: SQLAlchemyAsyncSession = db
        # Map pydantic enum to ORM enum
        orm_state = TaskStateEnum(new_state.value)
        stmt = (
            sql_update(Task)
            .where(Task.id.in_(task_ids))
            .values(state=orm_state)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    # --- Custom methods for Observer ---

    async def get_task_statistics(
        self, db: DatabaseSession, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        session: SQLAlchemyAsyncSession = db
        stmt = (
            select(Task.state, func.count(Task.id).label("count"))
            .where(Task.user_id == user_id)
            .where(Task.created_at >= start_date)
            .where(Task.created_at <= end_date)
            .group_by(Task.state)
        )
        result = await session.execute(stmt)
        stats = {row.state.value: row.count for row in result}
        return stats
