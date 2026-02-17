"""SQLAlchemy concrete factory — creates SQLAlchemy DAO implementations."""

from dao_service.dao.impl.sqlalchemy.dao_user import DaoUser
from dao_service.dao.impl.sqlalchemy.dao_goal import DaoGoal
from dao_service.dao.impl.sqlalchemy.dao_milestone import DaoMilestone
from dao_service.dao.impl.sqlalchemy.dao_task import DaoTask
from dao_service.dao.impl.sqlalchemy.dao_conversation import DaoConversation
from dao_service.dao.impl.sqlalchemy.dao_demo_flag import DaoDemoFlag


class DaoSqlalchemyFactory:
    """Creates SQLAlchemy-backed DAO instances."""

    def create_user_dao(self) -> DaoUser:
        return DaoUser()

    def create_goal_dao(self) -> DaoGoal:
        return DaoGoal()

    def create_milestone_dao(self) -> DaoMilestone:
        return DaoMilestone()

    def create_task_dao(self) -> DaoTask:
        return DaoTask()

    def create_conversation_dao(self) -> DaoConversation:
        return DaoConversation()

    def create_demo_flag_dao(self) -> DaoDemoFlag:
        return DaoDemoFlag()
