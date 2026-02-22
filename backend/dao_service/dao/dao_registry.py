"""
Framework selection registry.

Selects the DAO factory based on the ORM_FRAMEWORK config setting.
Provides convenience functions to get individual DAOs.
"""

from functools import lru_cache

from dao_service.config import ORMFramework, settings
from dao_service.dao.dao_factory import DaoFactoryProtocol
from dao_service.dao.factories.dao_sqlalchemy_factory import DaoSqlalchemyFactory

_FACTORY_REGISTRY: dict[ORMFramework, type] = {
    ORMFramework.SQLALCHEMY: DaoSqlalchemyFactory,
    # Future: ORMFramework.TORTOISE: DaoTortoiseFactory,
}


@lru_cache(maxsize=1)
def get_dao_factory() -> DaoFactoryProtocol:
    """Return the DAO factory for the configured ORM framework."""
    factory_class = _FACTORY_REGISTRY.get(settings.ORM_FRAMEWORK)
    if factory_class is None:
        raise ValueError(f"Unsupported ORM framework: {settings.ORM_FRAMEWORK}")
    return factory_class()


# Convenience getters
def get_user_dao():
    return get_dao_factory().create_user_dao()


def get_goal_dao():
    return get_dao_factory().create_goal_dao()


def get_task_dao():
    return get_dao_factory().create_task_dao()


def get_conversation_dao():
    return get_dao_factory().create_conversation_dao()


def get_pattern_dao():
    return get_dao_factory().create_pattern_dao()


def get_notification_log_dao():
    return get_dao_factory().create_notification_log_dao()
