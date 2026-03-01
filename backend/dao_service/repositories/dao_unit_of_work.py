"""
Unit of Work pattern for ACID transactions across multiple DAOs.

Provides atomic multi-entity operations — if any operation fails,
all changes within the context are rolled back.
"""

from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_registry import get_dao_factory


class DaoUnitOfWork:
    """
    Framework-agnostic transaction coordinator.

    Usage:
        async with DaoUnitOfWork(db) as uow:
            goal = await uow.goals.create(db, goal_data)
            task = await uow.tasks.create(db, task_data)
            # If ANY fails, ALL are rolled back
    """

    def __init__(self, db: DatabaseSession):
        self.db = db
        factory = get_dao_factory()
        self.users = factory.create_user_dao()
        self.goals = factory.create_goal_dao()
        self.tasks = factory.create_task_dao()
        self.conversations = factory.create_conversation_dao()
        self.patterns = factory.create_pattern_dao()
        self.notification_logs = factory.create_notification_log_dao()
        self.messages = factory.create_message_dao()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        # Note: commit is NOT called here — the get_db() dependency handles it.
        # UoW only rolls back on error. This avoids double-commit issues.

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()
