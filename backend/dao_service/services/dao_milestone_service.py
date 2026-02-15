"""Data validation service for milestones. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.core.exceptions import ForeignKeyError
from dao_service.dao.dao_protocols import GoalDAOProtocol, MilestoneDAOProtocol
from dao_service.dao.dao_registry import get_goal_dao, get_milestone_dao
from dao_service.schemas.milestone import MilestoneCreateDTO, MilestoneDTO, MilestoneUpdateDTO


class DaoMilestoneService:
    def __init__(self):
        self.milestone_dao: MilestoneDAOProtocol = get_milestone_dao()
        self.goal_dao: GoalDAOProtocol = get_goal_dao()

    async def get_milestones(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[MilestoneDTO]:
        if limit > 100:
            limit = 100
        return await self.milestone_dao.get_multi(db, skip=skip, limit=limit)

    async def count_milestones(self, db: DatabaseSession) -> int:
        return await self.milestone_dao.count(db)

    async def get_milestone(self, db: DatabaseSession, milestone_id: UUID) -> Optional[MilestoneDTO]:
        return await self.milestone_dao.get_by_id(db, milestone_id)

    async def create_milestone(
        self, db: DatabaseSession, data: MilestoneCreateDTO
    ) -> MilestoneDTO:
        # FK check: goal must exist
        goal = await self.goal_dao.get_by_id(db, data.goal_id)
        if not goal:
            raise ForeignKeyError("goal_id", str(data.goal_id))
        return await self.milestone_dao.create(db, data)

    async def update_milestone(
        self, db: DatabaseSession, milestone_id: UUID, data: MilestoneUpdateDTO
    ) -> Optional[MilestoneDTO]:
        return await self.milestone_dao.update(db, milestone_id, data)

    async def delete_milestone(self, db: DatabaseSession, milestone_id: UUID) -> bool:
        return await self.milestone_dao.delete(db, milestone_id)
