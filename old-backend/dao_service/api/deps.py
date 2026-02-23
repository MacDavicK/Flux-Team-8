"""
FastAPI dependencies: database session, service key auth, service factories.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from dao_service.config import settings
from dao_service.core.database import DatabaseSession, get_db  # noqa: F401 — re-export
from dao_service.services.dao_user_service import DaoUserService
from dao_service.services.dao_goal_service import DaoGoalService
from dao_service.services.dao_task_service import DaoTaskService
from dao_service.services.dao_milestone_service import DaoMilestoneService
from dao_service.services.dao_conversation_service import DaoConversationService

# --- Service key authentication ---

api_key_header = APIKeyHeader(name="X-Flux-Service-Key", auto_error=False)


async def verify_service_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the caller is a registered Flux microservice."""
    if not api_key or api_key not in settings.SERVICE_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing service API key",
        )
    return api_key


# --- Service factory dependencies ---


def get_user_service() -> DaoUserService:
    return DaoUserService()


def get_goal_service() -> DaoGoalService:
    return DaoGoalService()


def get_task_service() -> DaoTaskService:
    return DaoTaskService()


def get_milestone_service() -> DaoMilestoneService:
    return DaoMilestoneService()


def get_conversation_service() -> DaoConversationService:
    return DaoConversationService()
