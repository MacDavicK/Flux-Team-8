"""Data validation service for goals. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.core.exceptions import ForeignKeyError
from dao_service.dao.dao_protocols import GoalDAOProtocol, UserDAOProtocol
from dao_service.dao.dao_registry import get_goal_dao, get_user_dao
from dao_service.repositories.dao_unit_of_work import DaoUnitOfWork
from dao_service.schemas.goal import (
    GoalCreateDTO,
    GoalDTO,
    GoalStructureCreateDTO,
    GoalUpdateDTO,
    GoalWithRelationsDTO,
    MilestoneInGoalDTO,
    TaskInGoalDTO,
)
from dao_service.schemas.milestone import MilestoneCreateDTO
from dao_service.schemas.task import TaskCreateDTO


class DaoGoalService:
    def __init__(self):
        self.goal_dao: GoalDAOProtocol = get_goal_dao()
        self.user_dao: UserDAOProtocol = get_user_dao()

    async def get_goals(self, db: DatabaseSession, skip: int = 0, limit: int = 100) -> List[GoalDTO]:
        if limit > 100:
            limit = 100
        return await self.goal_dao.get_multi(db, skip=skip, limit=limit)

    async def count_goals(self, db: DatabaseSession) -> int:
        return await self.goal_dao.count(db)

    async def get_goal(self, db: DatabaseSession, goal_id: UUID) -> Optional[GoalDTO]:
        return await self.goal_dao.get_by_id(db, goal_id)

    async def get_goal_full(self, db: DatabaseSession, goal_id: UUID) -> Optional[GoalWithRelationsDTO]:
        """Get goal with milestones and tasks eagerly loaded."""
        result = await self.goal_dao.get_with_relations(db, goal_id)
        if result is None:
            return None
        goal = result["goal"]
        return GoalWithRelationsDTO(
            id=goal.id,
            user_id=goal.user_id,
            title=goal.title,
            category=goal.category,
            timeline=goal.timeline,
            status=goal.status,
            created_at=goal.created_at,
            milestones=[MilestoneInGoalDTO.model_validate(m) for m in result["milestones"]],
            tasks=[TaskInGoalDTO.model_validate(t) for t in result["tasks"]],
        )

    async def create_goal(self, db: DatabaseSession, data: GoalCreateDTO) -> GoalDTO:
        return await self.goal_dao.create(db, data)

    async def create_goal_with_structure(
        self, db: DatabaseSession, data: GoalStructureCreateDTO
    ) -> GoalWithRelationsDTO:
        """Atomically create goal + milestones + tasks via Unit of Work."""
        async with DaoUnitOfWork(db) as uow:
            # Create goal
            goal = await uow.goals.create(db, data.goal)

            milestones = []
            tasks = []

            for ms_data in data.milestones:
                milestone = await uow.milestones.create(
                    db,
                    MilestoneCreateDTO(
                        goal_id=goal.id,
                        week_number=ms_data.week_number,
                        title=ms_data.title,
                        status=ms_data.status,
                    ),
                )
                milestones.append(milestone)

                for task_data in ms_data.tasks:
                    task = await uow.tasks.create(
                        db,
                        TaskCreateDTO(
                            user_id=data.goal.user_id,
                            goal_id=goal.id,
                            milestone_id=milestone.id,
                            title=task_data.title,
                            start_time=task_data.start_time,
                            end_time=task_data.end_time,
                            state=task_data.state,
                            priority=task_data.priority,
                            trigger_type=task_data.trigger_type,
                            is_recurring=task_data.is_recurring,
                        ),
                    )
                    tasks.append(task)

        return GoalWithRelationsDTO(
            id=goal.id,
            user_id=goal.user_id,
            title=goal.title,
            category=goal.category,
            timeline=goal.timeline,
            status=goal.status,
            created_at=goal.created_at,
            milestones=[
                MilestoneInGoalDTO(
                    id=m.id,
                    week_number=m.week_number,
                    title=m.title,
                    status=m.status,
                    created_at=m.created_at,
                )
                for m in milestones
            ],
            tasks=[
                TaskInGoalDTO(
                    id=t.id,
                    title=t.title,
                    state=t.state,
                    priority=t.priority,
                    milestone_id=t.milestone_id,
                    created_at=t.created_at,
                )
                for t in tasks
            ],
        )

    async def update_goal(
        self, db: DatabaseSession, goal_id: UUID, data: GoalUpdateDTO
    ) -> Optional[GoalDTO]:
        return await self.goal_dao.update(db, goal_id, data)

    async def delete_goal(self, db: DatabaseSession, goal_id: UUID) -> bool:
        return await self.goal_dao.delete(db, goal_id)
