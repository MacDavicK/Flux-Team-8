"""
Data validation service for tasks. NO business logic.

Responsibilities:
- Data format validation (Pydantic handles this)
- Technical limits (pagination cap)
- Optional FK existence checks
- NO business logic (belongs in Goal Planner/Scheduler/Observer)
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.core.exceptions import ForeignKeyError
from dao_service.dao.dao_protocols import MilestoneDAOProtocol, TaskDAOProtocol
from dao_service.dao.dao_registry import get_milestone_dao, get_task_dao
from dao_service.schemas.enums import TaskState
from dao_service.schemas.task import TaskCreateDTO, TaskDTO, TaskStatisticsDTO, TaskUpdateDTO


class DaoTaskService:
    def __init__(self):
        self.task_dao: TaskDAOProtocol = get_task_dao()
        self.milestone_dao: MilestoneDAOProtocol = get_milestone_dao()

    async def get_tasks(self, db: DatabaseSession, skip: int = 0, limit: int = 100) -> List[TaskDTO]:
        if limit > 100:
            limit = 100
        return await self.task_dao.get_multi(db, skip=skip, limit=limit)

    async def count_tasks(self, db: DatabaseSession) -> int:
        return await self.task_dao.count(db)

    async def get_task(self, db: DatabaseSession, task_id: UUID) -> Optional[TaskDTO]:
        return await self.task_dao.get_by_id(db, task_id)

    async def create_task(self, db: DatabaseSession, task_data: TaskCreateDTO) -> TaskDTO:
        """Create task with FK integrity check."""
        if task_data.milestone_id:
            milestone = await self.milestone_dao.get_by_id(db, task_data.milestone_id)
            if not milestone:
                raise ForeignKeyError("milestone_id", str(task_data.milestone_id))
        return await self.task_dao.create(db, task_data)

    async def update_task(
        self, db: DatabaseSession, task_id: UUID, data: TaskUpdateDTO
    ) -> Optional[TaskDTO]:
        return await self.task_dao.update(db, task_id, data)

    async def delete_task(self, db: DatabaseSession, task_id: UUID) -> bool:
        return await self.task_dao.delete(db, task_id)

    # --- Scheduler endpoints ---

    async def get_tasks_for_scheduling(
        self, db: DatabaseSession, user_id: UUID, start_time: datetime, end_time: datetime
    ) -> List[TaskDTO]:
        return await self.task_dao.get_tasks_by_user_and_timerange(db, user_id, start_time, end_time)

    async def bulk_update_state(
        self, db: DatabaseSession, task_ids: List[UUID], new_state: TaskState
    ) -> int:
        return await self.task_dao.bulk_update_state(db, task_ids, new_state)

    async def update_calendar_event_id(
        self, db: DatabaseSession, task_id: UUID, calendar_event_id: str
    ) -> Optional[TaskDTO]:
        return await self.task_dao.update_calendar_event_id(db, task_id, calendar_event_id)

    # --- Observer endpoints ---

    async def get_task_statistics(
        self, db: DatabaseSession, user_id: UUID, start_date: datetime, end_date: datetime
    ) -> TaskStatisticsDTO:
        stats = await self.task_dao.get_task_statistics(db, user_id, start_date, end_date)
        total = sum(stats.values())
        completed = stats.get("completed", 0)
        completion_rate = completed / total if total > 0 else 0.0
        return TaskStatisticsDTO(
            user_id=user_id,
            total_tasks=total,
            by_state=stats,
            completion_rate=round(completion_rate, 4),
        )
