"""SQLAlchemy concrete factory — creates SQLAlchemy DAO implementations."""

from dao_service.dao.impl.sqlalchemy.dao_conversation import DaoConversation
from dao_service.dao.impl.sqlalchemy.dao_goal import DaoGoal
from dao_service.dao.impl.sqlalchemy.dao_message import DaoMessage
from dao_service.dao.impl.sqlalchemy.dao_notification_log import DaoNotificationLog
from dao_service.dao.impl.sqlalchemy.dao_pattern import DaoPattern
from dao_service.dao.impl.sqlalchemy.dao_task import DaoTask
from dao_service.dao.impl.sqlalchemy.dao_user import DaoUser


class DaoSqlalchemyFactory:
    """Creates SQLAlchemy-backed DAO instances."""

    def create_user_dao(self) -> DaoUser:
        return DaoUser()

    def create_goal_dao(self) -> DaoGoal:
        return DaoGoal()

    def create_task_dao(self) -> DaoTask:
        return DaoTask()

    def create_conversation_dao(self) -> DaoConversation:
        return DaoConversation()

    def create_pattern_dao(self) -> DaoPattern:
        return DaoPattern()

    def create_notification_log_dao(self) -> DaoNotificationLog:
        return DaoNotificationLog()

    def create_message_dao(self) -> DaoMessage:
        return DaoMessage()
