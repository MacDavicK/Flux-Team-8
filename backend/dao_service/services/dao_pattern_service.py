"""Data validation service for patterns. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_protocols import PatternDAOProtocol
from dao_service.dao.dao_registry import get_pattern_dao
from dao_service.schemas.pattern import PatternCreateDTO, PatternDTO, PatternUpdateDTO


class DaoPatternService:
    def __init__(self):
        self.pattern_dao: PatternDAOProtocol = get_pattern_dao()

    async def get_patterns(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[PatternDTO]:
        if limit > 100:
            limit = 100
        return await self.pattern_dao.get_multi(db, skip=skip, limit=limit)

    async def count_patterns(self, db: DatabaseSession) -> int:
        return await self.pattern_dao.count(db)

    async def get_pattern(self, db: DatabaseSession, pattern_id: UUID) -> Optional[PatternDTO]:
        return await self.pattern_dao.get_by_id(db, pattern_id)

    async def create_pattern(self, db: DatabaseSession, data: PatternCreateDTO) -> PatternDTO:
        return await self.pattern_dao.create(db, data)

    async def update_pattern(
        self, db: DatabaseSession, pattern_id: UUID, data: PatternUpdateDTO
    ) -> Optional[PatternDTO]:
        return await self.pattern_dao.update(db, pattern_id, data)

    async def delete_pattern(self, db: DatabaseSession, pattern_id: UUID) -> bool:
        return await self.pattern_dao.delete(db, pattern_id)
