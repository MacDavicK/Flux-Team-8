"""Data validation service for goals. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_protocols import GoalDAOProtocol, UserDAOProtocol
from dao_service.dao.dao_registry import get_goal_dao, get_user_dao
from dao_service.schemas.goal import GoalCreateDTO, GoalDTO, GoalUpdateDTO


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

    async def create_goal(self, db: DatabaseSession, data: GoalCreateDTO) -> GoalDTO:
        return await self.goal_dao.create(db, data)

    async def update_goal(
        self, db: DatabaseSession, goal_id: UUID, data: GoalUpdateDTO
    ) -> Optional[GoalDTO]:
        return await self.goal_dao.update(db, goal_id, data)

    async def delete_goal(self, db: DatabaseSession, goal_id: UUID) -> bool:
        return await self.goal_dao.delete(db, goal_id)
