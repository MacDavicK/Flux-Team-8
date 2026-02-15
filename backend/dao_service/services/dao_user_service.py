"""Data validation service for users. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_protocols import UserDAOProtocol
from dao_service.dao.dao_registry import get_user_dao
from dao_service.schemas.user import UserCreateDTO, UserDTO, UserUpdateDTO


class DaoUserService:
    def __init__(self):
        self.user_dao: UserDAOProtocol = get_user_dao()

    async def get_users(self, db: DatabaseSession, skip: int = 0, limit: int = 100) -> List[UserDTO]:
        if limit > 100:
            limit = 100
        return await self.user_dao.get_multi(db, skip=skip, limit=limit)

    async def count_users(self, db: DatabaseSession) -> int:
        return await self.user_dao.count(db)

    async def get_user(self, db: DatabaseSession, user_id: UUID) -> Optional[UserDTO]:
        return await self.user_dao.get_by_id(db, user_id)

    async def create_user(self, db: DatabaseSession, data: UserCreateDTO) -> UserDTO:
        return await self.user_dao.create(db, data)

    async def update_user(
        self, db: DatabaseSession, user_id: UUID, data: UserUpdateDTO
    ) -> Optional[UserDTO]:
        return await self.user_dao.update(db, user_id, data)

    async def delete_user(self, db: DatabaseSession, user_id: UUID) -> bool:
        return await self.user_dao.delete(db, user_id)
