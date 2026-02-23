"""Data validation service for conversations. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_protocols import ConversationDAOProtocol
from dao_service.dao.dao_registry import get_conversation_dao
from dao_service.schemas.conversation import ConversationCreateDTO, ConversationDTO, ConversationUpdateDTO


class DaoConversationService:
    def __init__(self):
        self.conversation_dao: ConversationDAOProtocol = get_conversation_dao()

    async def get_conversations(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[ConversationDTO]:
        if limit > 100:
            limit = 100
        return await self.conversation_dao.get_multi(db, skip=skip, limit=limit)

    async def count_conversations(self, db: DatabaseSession) -> int:
        return await self.conversation_dao.count(db)

    async def get_conversation(
        self, db: DatabaseSession, conversation_id: UUID
    ) -> Optional[ConversationDTO]:
        return await self.conversation_dao.get_by_id(db, conversation_id)

    async def create_conversation(
        self, db: DatabaseSession, data: ConversationCreateDTO
    ) -> ConversationDTO:
        return await self.conversation_dao.create(db, data)

    async def update_conversation(
        self, db: DatabaseSession, conversation_id: UUID, data: ConversationUpdateDTO
    ) -> Optional[ConversationDTO]:
        return await self.conversation_dao.update(db, conversation_id, data)
