"""Abstract factory protocol for creating DAOs."""

from typing import Protocol

from dao_service.dao.dao_protocols import (
    ConversationDAOProtocol,
    GoalDAOProtocol,
    NotificationLogDAOProtocol,
    PatternDAOProtocol,
    TaskDAOProtocol,
    UserDAOProtocol,
)


class DaoFactoryProtocol(Protocol):
    """Abstract factory that creates DAO instances for the configured ORM."""

    def create_user_dao(self) -> UserDAOProtocol: ...
    def create_goal_dao(self) -> GoalDAOProtocol: ...
    def create_task_dao(self) -> TaskDAOProtocol: ...
    def create_conversation_dao(self) -> ConversationDAOProtocol: ...
    def create_pattern_dao(self) -> PatternDAOProtocol: ...
    def create_notification_log_dao(self) -> NotificationLogDAOProtocol: ...
