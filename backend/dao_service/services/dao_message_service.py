"""Data validation service for messages. No business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_protocols import MessageDAOProtocol
from dao_service.dao.dao_registry import get_message_dao
from dao_service.schemas.message import MessageCreateDTO, MessageDTO


class DaoMessageService:
    """Thin service layer for message persistence — data validation only."""

    def __init__(self):
        self.message_dao: MessageDAOProtocol = get_message_dao()

    async def get_messages_for_conversation(
        self, db: DatabaseSession, conversation_id: UUID
    ) -> List[MessageDTO]:
        """Retrieve all messages for a conversation."""
        return await self.message_dao.get_by_conversation(db, conversation_id)

    async def get_message(self, db: DatabaseSession, message_id: UUID) -> Optional[MessageDTO]:
        """Retrieve a single message by ID."""
        return await self.message_dao.get_by_id(db, message_id)

    async def create_message(self, db: DatabaseSession, data: MessageCreateDTO) -> MessageDTO:
        """Create a new message."""
        return await self.message_dao.create(db, data)

    async def delete_message(self, db: DatabaseSession, message_id: UUID) -> bool:
        """Delete a message by ID."""
        return await self.message_dao.delete(db, message_id)

    async def count_messages_for_conversation(
        self, db: DatabaseSession, conversation_id: UUID
    ) -> int:
        """Count messages for a conversation."""
        return await self.message_dao.count_by_conversation(db, conversation_id)
