"""Abstract factory protocol for creating DAOs."""

from typing import Protocol

from dao_service.dao.dao_protocols import (
    ConversationDAOProtocol,
    DemoFlagDAOProtocol,
    GoalDAOProtocol,
    MilestoneDAOProtocol,
    TaskDAOProtocol,
    UserDAOProtocol,
)


class DaoFactoryProtocol(Protocol):
    """Abstract factory that creates DAO instances for the configured ORM."""

    def create_user_dao(self) -> UserDAOProtocol: ...
    def create_goal_dao(self) -> GoalDAOProtocol: ...
    def create_milestone_dao(self) -> MilestoneDAOProtocol: ...
    def create_task_dao(self) -> TaskDAOProtocol: ...
    def create_conversation_dao(self) -> ConversationDAOProtocol: ...
    def create_demo_flag_dao(self) -> DemoFlagDAOProtocol: ...
