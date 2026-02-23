"""Data validation service for notification logs. NO business logic."""

from typing import List, Optional
from uuid import UUID

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_protocols import NotificationLogDAOProtocol
from dao_service.dao.dao_registry import get_notification_log_dao
from dao_service.schemas.notification_log import (
    NotificationLogCreateDTO,
    NotificationLogDTO,
    NotificationLogUpdateDTO,
)


class DaoNotificationLogService:
    def __init__(self):
        self.notification_log_dao: NotificationLogDAOProtocol = get_notification_log_dao()

    async def get_notification_logs(
        self, db: DatabaseSession, skip: int = 0, limit: int = 100
    ) -> List[NotificationLogDTO]:
        if limit > 100:
            limit = 100
        return await self.notification_log_dao.get_multi(db, skip=skip, limit=limit)

    async def count_notification_logs(self, db: DatabaseSession) -> int:
        return await self.notification_log_dao.count(db)

    async def get_notification_log(
        self, db: DatabaseSession, notification_log_id: UUID
    ) -> Optional[NotificationLogDTO]:
        return await self.notification_log_dao.get_by_id(db, notification_log_id)

    async def create_notification_log(
        self, db: DatabaseSession, data: NotificationLogCreateDTO
    ) -> NotificationLogDTO:
        return await self.notification_log_dao.create(db, data)

    async def update_notification_log(
        self, db: DatabaseSession, notification_log_id: UUID, data: NotificationLogUpdateDTO
    ) -> Optional[NotificationLogDTO]:
        return await self.notification_log_dao.update(db, notification_log_id, data)

    async def delete_notification_log(self, db: DatabaseSession, notification_log_id: UUID) -> bool:
        return await self.notification_log_dao.delete(db, notification_log_id)
