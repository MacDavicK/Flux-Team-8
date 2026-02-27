"""
Unit tests for the DAO service layer.

Each service's DAO dependency is replaced with a MagicMock/AsyncMock —
no real database, no real DAO implementation, no network calls required.

Tests verify:
- Services delegate to DAOs with correct arguments
- Pagination limit is capped at 100 in every list method
- DaoTaskService.get_task_statistics contains real business logic:
    completion_rate = done / total, rounded to 4 decimal places
    zero-division is handled gracefully
- DaoConversationService has no delete_conversation method (audit trail design)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from dao_service.schemas.conversation import ConversationCreateDTO, ConversationDTO
from dao_service.schemas.goal import GoalCreateDTO, GoalDTO
from dao_service.schemas.task import TaskDTO, TaskStatisticsDTO
from dao_service.schemas.user import UserCreateDTO, UserDTO
from dao_service.services.dao_conversation_service import DaoConversationService
from dao_service.services.dao_goal_service import DaoGoalService
from dao_service.services.dao_task_service import DaoTaskService
from dao_service.services.dao_user_service import DaoUserService


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_db():
    """Minimal stand-in for a DatabaseSession."""
    return AsyncMock()


def _make_user_dto(**kw) -> UserDTO:
    return UserDTO(
        id=kw.get("id", uuid4()),
        email=kw.get("email", "u@flux.test"),
        onboarded=kw.get("onboarded", False),
        created_at=kw.get("created_at", _now()),
    )


def _make_goal_dto(**kw) -> GoalDTO:
    return GoalDTO(
        id=kw.get("id", uuid4()),
        user_id=kw.get("user_id", uuid4()),
        title=kw.get("title", "Test Goal"),
        status=kw.get("status", "active"),
        target_weeks=6,
        created_at=kw.get("created_at", _now()),
    )


def _make_task_dto(**kw) -> TaskDTO:
    return TaskDTO(
        id=kw.get("id", uuid4()),
        user_id=kw.get("user_id", uuid4()),
        title=kw.get("title", "Test Task"),
        status=kw.get("status", "pending"),
        trigger_type="time",
        created_at=kw.get("created_at", _now()),
    )


def _make_conversation_dto(**kw) -> ConversationDTO:
    return ConversationDTO(
        id=kw.get("id", uuid4()),
        user_id=kw.get("user_id", uuid4()),
        langgraph_thread_id=kw.get("langgraph_thread_id", f"thread-{uuid4().hex}"),
        context_type=kw.get("context_type", "goal"),
        created_at=kw.get("created_at", _now()),
    )


# Service factories — bypass __init__ so the DAO registry is never touched.

def _user_service(mock_dao) -> DaoUserService:
    svc = DaoUserService.__new__(DaoUserService)
    svc.user_dao = mock_dao
    return svc


def _goal_service(mock_goal_dao, mock_user_dao=None) -> DaoGoalService:
    svc = DaoGoalService.__new__(DaoGoalService)
    svc.goal_dao = mock_goal_dao
    svc.user_dao = mock_user_dao or MagicMock()
    return svc


def _task_service(mock_dao) -> DaoTaskService:
    svc = DaoTaskService.__new__(DaoTaskService)
    svc.task_dao = mock_dao
    return svc


def _conversation_service(mock_dao) -> DaoConversationService:
    svc = DaoConversationService.__new__(DaoConversationService)
    svc.conversation_dao = mock_dao
    return svc


# ── DaoUserService ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoUserService:
    async def test_get_users_delegates_to_dao(self):
        mock_dao = MagicMock()
        expected = [_make_user_dto()]
        mock_dao.get_multi = AsyncMock(return_value=expected)
        svc = _user_service(mock_dao)

        result = await svc.get_users(_mock_db(), skip=0, limit=10)

        mock_dao.get_multi.assert_called_once()
        assert result == expected

    async def test_get_users_caps_limit_at_100(self):
        mock_dao = MagicMock()
        mock_dao.get_multi = AsyncMock(return_value=[])
        svc = _user_service(mock_dao)

        await svc.get_users(_mock_db(), skip=0, limit=999)

        _, kwargs = mock_dao.get_multi.call_args
        assert kwargs["limit"] == 100

    async def test_count_users_delegates_to_dao(self):
        mock_dao = MagicMock()
        mock_dao.count = AsyncMock(return_value=42)
        svc = _user_service(mock_dao)

        assert await svc.count_users(_mock_db()) == 42

    async def test_get_user_returns_none_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id = AsyncMock(return_value=None)
        svc = _user_service(mock_dao)

        assert await svc.get_user(_mock_db(), uuid4()) is None

    async def test_create_user_delegates_to_dao(self):
        mock_dao = MagicMock()
        expected = _make_user_dto(email="new@flux.test")
        mock_dao.create = AsyncMock(return_value=expected)
        svc = _user_service(mock_dao)

        result = await svc.create_user(_mock_db(), UserCreateDTO(email="new@flux.test"))

        assert result.email == "new@flux.test"

    async def test_update_user_delegates_to_dao(self):
        mock_dao = MagicMock()
        expected = _make_user_dto(onboarded=True)
        mock_dao.update = AsyncMock(return_value=expected)
        svc = _user_service(mock_dao)

        from dao_service.schemas.user import UserUpdateDTO
        result = await svc.update_user(_mock_db(), uuid4(), UserUpdateDTO(onboarded=True))

        assert result is not None
        assert result.onboarded is True

    async def test_delete_user_returns_false_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=False)
        svc = _user_service(mock_dao)

        assert await svc.delete_user(_mock_db(), uuid4()) is False

    async def test_delete_user_returns_true_when_found(self):
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=True)
        svc = _user_service(mock_dao)

        assert await svc.delete_user(_mock_db(), uuid4()) is True


# ── DaoGoalService ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoGoalService:
    async def test_get_goals_caps_limit_at_100(self):
        mock_dao = MagicMock()
        mock_dao.get_multi = AsyncMock(return_value=[])
        svc = _goal_service(mock_dao)

        await svc.get_goals(_mock_db(), skip=0, limit=500)

        _, kwargs = mock_dao.get_multi.call_args
        assert kwargs["limit"] == 100

    async def test_create_goal_delegates_to_dao(self):
        mock_dao = MagicMock()
        user_id = uuid4()
        expected = _make_goal_dto(user_id=user_id, title="Learn to surf")
        mock_dao.create = AsyncMock(return_value=expected)
        svc = _goal_service(mock_dao)

        result = await svc.create_goal(
            _mock_db(), GoalCreateDTO(user_id=user_id, title="Learn to surf")
        )

        assert result.title == "Learn to surf"

    async def test_get_goal_returns_none_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id = AsyncMock(return_value=None)
        svc = _goal_service(mock_dao)

        assert await svc.get_goal(_mock_db(), uuid4()) is None

    async def test_delete_goal_returns_true_when_found(self):
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=True)
        svc = _goal_service(mock_dao)

        assert await svc.delete_goal(_mock_db(), uuid4()) is True

    async def test_delete_goal_returns_false_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.delete = AsyncMock(return_value=False)
        svc = _goal_service(mock_dao)

        assert await svc.delete_goal(_mock_db(), uuid4()) is False


# ── DaoTaskService ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoTaskService:
    async def test_get_tasks_caps_limit_at_100(self):
        mock_dao = MagicMock()
        mock_dao.get_multi = AsyncMock(return_value=[])
        svc = _task_service(mock_dao)

        await svc.get_tasks(_mock_db(), skip=0, limit=200)

        _, kwargs = mock_dao.get_multi.call_args
        assert kwargs["limit"] == 100

    async def test_bulk_update_status_delegates_to_dao(self):
        mock_dao = MagicMock()
        mock_dao.bulk_update_status = AsyncMock(return_value=3)
        svc = _task_service(mock_dao)

        count = await svc.bulk_update_status(_mock_db(), [uuid4(), uuid4(), uuid4()], "rescheduled")

        assert count == 3

    async def test_get_task_statistics_computes_completion_rate(self):
        """completion_rate = done / total, rounded to 4 decimal places."""
        mock_dao = MagicMock()
        mock_dao.get_task_statistics = AsyncMock(
            return_value={"done": 3, "pending": 1, "missed": 1}
        )
        svc = _task_service(mock_dao)

        now = _now()
        result = await svc.get_task_statistics(
            _mock_db(), uuid4(), now - timedelta(days=7), now
        )

        assert isinstance(result, TaskStatisticsDTO)
        assert result.total_tasks == 5
        assert result.by_status["done"] == 3
        assert result.completion_rate == round(3 / 5, 4)

    async def test_get_task_statistics_zero_tasks_no_division_error(self):
        """Completion rate is 0.0 when there are no tasks."""
        mock_dao = MagicMock()
        mock_dao.get_task_statistics = AsyncMock(return_value={})
        svc = _task_service(mock_dao)

        now = _now()
        result = await svc.get_task_statistics(
            _mock_db(), uuid4(), now - timedelta(days=7), now
        )

        assert result.total_tasks == 0
        assert result.completion_rate == 0.0

    async def test_get_task_statistics_all_done(self):
        """100% completion rate."""
        mock_dao = MagicMock()
        mock_dao.get_task_statistics = AsyncMock(return_value={"done": 5})
        svc = _task_service(mock_dao)

        now = _now()
        result = await svc.get_task_statistics(
            _mock_db(), uuid4(), now - timedelta(days=7), now
        )

        assert result.total_tasks == 5
        assert result.completion_rate == 1.0

    async def test_get_task_statistics_no_done_tasks(self):
        """Completion rate is 0.0 when no tasks have status 'done'."""
        mock_dao = MagicMock()
        mock_dao.get_task_statistics = AsyncMock(return_value={"pending": 4, "missed": 1})
        svc = _task_service(mock_dao)

        now = _now()
        result = await svc.get_task_statistics(
            _mock_db(), uuid4(), now - timedelta(days=7), now
        )

        assert result.total_tasks == 5
        assert result.completion_rate == 0.0

    async def test_get_tasks_for_scheduling_delegates_to_dao(self):
        mock_dao = MagicMock()
        expected = [_make_task_dto()]
        mock_dao.get_tasks_by_user_and_timerange = AsyncMock(return_value=expected)
        svc = _task_service(mock_dao)

        now = _now()
        result = await svc.get_tasks_for_scheduling(
            _mock_db(), uuid4(), now - timedelta(hours=1), now + timedelta(hours=1)
        )

        assert result == expected


# ── DaoConversationService ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoConversationService:
    async def test_has_no_delete_conversation_method(self):
        """Conversations are immutable audit records — no delete is intentional."""
        svc = DaoConversationService.__new__(DaoConversationService)
        assert not hasattr(svc, "delete_conversation")

    async def test_get_conversations_caps_limit_at_100(self):
        mock_dao = MagicMock()
        mock_dao.get_multi = AsyncMock(return_value=[])
        svc = _conversation_service(mock_dao)

        await svc.get_conversations(_mock_db(), skip=0, limit=500)

        _, kwargs = mock_dao.get_multi.call_args
        assert kwargs["limit"] == 100

    async def test_create_conversation_delegates_to_dao(self):
        mock_dao = MagicMock()
        user_id = uuid4()
        expected = _make_conversation_dto(user_id=user_id, context_type="onboarding")
        mock_dao.create = AsyncMock(return_value=expected)
        svc = _conversation_service(mock_dao)

        result = await svc.create_conversation(
            _mock_db(),
            ConversationCreateDTO(
                user_id=user_id,
                langgraph_thread_id="thread-xyz",
                context_type="onboarding",
            ),
        )

        assert result.context_type == "onboarding"

    async def test_get_conversation_returns_none_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id = AsyncMock(return_value=None)
        svc = _conversation_service(mock_dao)

        assert await svc.get_conversation(_mock_db(), uuid4()) is None

    async def test_update_conversation_returns_none_when_not_found(self):
        mock_dao = MagicMock()
        mock_dao.update = AsyncMock(return_value=None)
        svc = _conversation_service(mock_dao)

        from dao_service.schemas.conversation import ConversationUpdateDTO
        result = await svc.update_conversation(
            _mock_db(), uuid4(), ConversationUpdateDTO(context_type="task")
        )

        assert result is None
