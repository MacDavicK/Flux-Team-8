"""
Unit tests for SQLAlchemy DAO implementations.

All database interactions are replaced with AsyncMock — no real database
connection or Supabase instance is required.

Tests verify that each DAO method:
- Calls the correct session operations (add/flush/refresh/execute/delete)
- Maps ORM objects to DTOs correctly
- Returns None / False on not-found paths
- DaoConversation deliberately has no delete method (audit trail design)
- DaoTask scheduler / observer custom methods return the right types
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from dao_service.dao.impl.sqlalchemy.dao_conversation import DaoConversation
from dao_service.dao.impl.sqlalchemy.dao_goal import DaoGoal
from dao_service.dao.impl.sqlalchemy.dao_task import DaoTask
from dao_service.dao.impl.sqlalchemy.dao_user import DaoUser
from dao_service.models.conversation_model import Conversation
from dao_service.models.goal_model import Goal
from dao_service.models.task_model import Task
from dao_service.models.user_model import User
from dao_service.schemas.conversation import ConversationCreateDTO, ConversationDTO, ConversationUpdateDTO
from dao_service.schemas.goal import GoalCreateDTO, GoalDTO, GoalUpdateDTO
from dao_service.schemas.task import TaskCreateDTO, TaskUpdateDTO
from dao_service.schemas.user import UserCreateDTO, UserUpdateDTO


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mock_session():
    """AsyncMock that behaves like an AsyncSession.
    session.add() is kept synchronous to match SQLAlchemy's API."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _result_scalar_one_or_none(obj):
    """Mock execute() result for single-row queries."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    return result


def _result_scalar_one(value):
    """Mock execute() result for aggregate (COUNT) queries."""
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _result_scalars_all(items):
    """Mock execute() result for list queries."""
    scalars = MagicMock()
    scalars.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


# ── ORM object factories ──────────────────────────────────────────────────────
#
# Use the normal SQLAlchemy constructor so that __init__ runs and sets up
# _sa_instance_state.  __new__ bypasses __init__ and leaves the instance in an
# uninstrumented state, causing AttributeError on any subsequent attribute set.


def _make_user(**kw) -> User:
    return User(
        id=kw.get("id", uuid4()),
        email=kw.get("email", "test@flux.test"),
        onboarded=kw.get("onboarded", False),
        profile=kw.get("profile", None),
        notification_preferences=kw.get("notification_preferences", None),
        created_at=kw.get("created_at", _now()),
    )


def _make_goal(**kw) -> Goal:
    return Goal(
        id=kw.get("id", uuid4()),
        user_id=kw.get("user_id", uuid4()),
        title=kw.get("title", "Test Goal"),
        description=kw.get("description", None),
        class_tags=kw.get("class_tags", None),
        status=kw.get("status", "active"),
        parent_goal_id=kw.get("parent_goal_id", None),
        pipeline_order=kw.get("pipeline_order", None),
        activated_at=kw.get("activated_at", None),
        completed_at=kw.get("completed_at", None),
        target_weeks=kw.get("target_weeks", 6),
        plan_json=kw.get("plan_json", None),
        created_at=kw.get("created_at", _now()),
    )


def _make_task(**kw) -> Task:
    return Task(
        id=kw.get("id", uuid4()),
        user_id=kw.get("user_id", uuid4()),
        goal_id=kw.get("goal_id", None),
        title=kw.get("title", "Test Task"),
        description=kw.get("description", None),
        status=kw.get("status", "pending"),
        scheduled_at=kw.get("scheduled_at", None),
        duration_minutes=kw.get("duration_minutes", None),
        trigger_type=kw.get("trigger_type", "time"),
        location_trigger=kw.get("location_trigger", None),
        reminder_sent_at=kw.get("reminder_sent_at", None),
        whatsapp_sent_at=kw.get("whatsapp_sent_at", None),
        call_sent_at=kw.get("call_sent_at", None),
        completed_at=kw.get("completed_at", None),
        recurrence_rule=kw.get("recurrence_rule", None),
        shared_with_goal_ids=kw.get("shared_with_goal_ids", None),
        created_at=kw.get("created_at", _now()),
    )


def _make_conversation(**kw) -> Conversation:
    return Conversation(
        id=kw.get("id", uuid4()),
        user_id=kw.get("user_id", uuid4()),
        langgraph_thread_id=kw.get("langgraph_thread_id", f"thread-{uuid4().hex}"),
        context_type=kw.get("context_type", "goal"),
        last_message_at=kw.get("last_message_at", None),
        created_at=kw.get("created_at", _now()),
    )


# ── DaoUser ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoUser:
    async def test_create_calls_add_flush_refresh_and_returns_dto(self):
        dao = DaoUser()
        db = _mock_session()
        created_id = uuid4()

        async def populate(obj):
            obj.id = created_id
            obj.created_at = _now()

        db.refresh = AsyncMock(side_effect=populate)

        result = await dao.create(db, UserCreateDTO(email="u@flux.test"))

        db.add.assert_called_once()
        db.flush.assert_called_once()
        db.refresh.assert_called_once()
        assert result.email == "u@flux.test"

    async def test_get_by_id_found(self):
        dao = DaoUser()
        db = _mock_session()
        user = _make_user()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(user))

        result = await dao.get_by_id(db, user.id)

        assert result is not None
        assert result.id == user.id

    async def test_get_by_id_not_found(self):
        dao = DaoUser()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        result = await dao.get_by_id(db, uuid4())

        assert result is None

    async def test_get_multi_returns_list_of_dtos(self):
        dao = DaoUser()
        db = _mock_session()
        users = [_make_user(email=f"u{i}@flux.test") for i in range(3)]
        db.execute = AsyncMock(return_value=_result_scalars_all(users))

        result = await dao.get_multi(db, skip=0, limit=10)

        assert len(result) == 3

    async def test_count_returns_integer(self):
        dao = DaoUser()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one(5))

        assert await dao.count(db) == 5

    async def test_update_applies_changes(self):
        dao = DaoUser()
        db = _mock_session()
        user = _make_user(onboarded=False)
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(user))
        db.refresh = AsyncMock()

        result = await dao.update(db, user.id, UserUpdateDTO(onboarded=True))

        assert result is not None
        assert result.onboarded is True

    async def test_update_not_found_returns_none(self):
        dao = DaoUser()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        result = await dao.update(db, uuid4(), UserUpdateDTO(onboarded=True))

        assert result is None

    async def test_delete_found_returns_true(self):
        dao = DaoUser()
        db = _mock_session()
        user = _make_user()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(user))

        found = await dao.delete(db, user.id)

        assert found is True
        db.delete.assert_called_once_with(user)
        db.flush.assert_called_once()

    async def test_delete_not_found_returns_false(self):
        dao = DaoUser()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        found = await dao.delete(db, uuid4())

        assert found is False
        db.delete.assert_not_called()


# ── DaoGoal ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoGoal:
    async def test_create_returns_goal_dto(self):
        dao = DaoGoal()
        db = _mock_session()
        user_id = uuid4()

        async def populate(obj):
            obj.id = uuid4()
            obj.created_at = _now()

        db.refresh = AsyncMock(side_effect=populate)

        result = await dao.create(db, GoalCreateDTO(user_id=user_id, title="Learn piano"))

        assert isinstance(result, GoalDTO)
        assert result.title == "Learn piano"
        assert result.user_id == user_id
        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_get_by_id_found(self):
        dao = DaoGoal()
        db = _mock_session()
        goal = _make_goal(title="Run a marathon")
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(goal))

        result = await dao.get_by_id(db, goal.id)

        assert result is not None
        assert result.title == "Run a marathon"

    async def test_get_by_id_not_found(self):
        dao = DaoGoal()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.get_by_id(db, uuid4()) is None

    async def test_get_multi_returns_list(self):
        dao = DaoGoal()
        db = _mock_session()
        goals = [_make_goal(title=f"Goal {i}") for i in range(3)]
        db.execute = AsyncMock(return_value=_result_scalars_all(goals))

        result = await dao.get_multi(db, skip=0, limit=3)

        assert len(result) == 3
        assert result[0].title == "Goal 0"

    async def test_count(self):
        dao = DaoGoal()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one(7))

        assert await dao.count(db) == 7

    async def test_update_applies_status_change(self):
        dao = DaoGoal()
        db = _mock_session()
        goal = _make_goal(status="active")
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(goal))
        db.refresh = AsyncMock()

        result = await dao.update(db, goal.id, GoalUpdateDTO(status="completed"))

        assert result is not None
        assert result.status == "completed"

    async def test_update_not_found_returns_none(self):
        dao = DaoGoal()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.update(db, uuid4(), GoalUpdateDTO(status="completed")) is None

    async def test_delete_found_returns_true(self):
        dao = DaoGoal()
        db = _mock_session()
        goal = _make_goal()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(goal))

        assert await dao.delete(db, goal.id) is True
        db.delete.assert_called_once_with(goal)

    async def test_delete_not_found_returns_false(self):
        dao = DaoGoal()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.delete(db, uuid4()) is False
        db.delete.assert_not_called()


# ── DaoTask ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoTask:
    async def test_create_returns_task_dto(self):
        dao = DaoTask()
        db = _mock_session()
        user_id = uuid4()

        async def populate(obj):
            obj.id = uuid4()
            obj.created_at = _now()

        db.refresh = AsyncMock(side_effect=populate)

        result = await dao.create(db, TaskCreateDTO(user_id=user_id, title="Go for a run"))

        assert result.title == "Go for a run"
        assert result.user_id == user_id

    async def test_get_by_id_not_found(self):
        dao = DaoTask()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.get_by_id(db, uuid4()) is None

    async def test_update_applies_status_change(self):
        dao = DaoTask()
        db = _mock_session()
        task = _make_task(status="pending")
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(task))
        db.refresh = AsyncMock()

        result = await dao.update(db, task.id, TaskUpdateDTO(status="done"))

        assert result is not None
        assert result.status == "done"

    async def test_update_not_found_returns_none(self):
        dao = DaoTask()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.update(db, uuid4(), TaskUpdateDTO(status="done")) is None

    async def test_delete_found_returns_true(self):
        dao = DaoTask()
        db = _mock_session()
        task = _make_task()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(task))

        assert await dao.delete(db, task.id) is True
        db.delete.assert_called_once_with(task)

    async def test_delete_not_found_returns_false(self):
        dao = DaoTask()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.delete(db, uuid4()) is False

    # -- Scheduler custom methods --

    async def test_bulk_update_status_returns_rowcount(self):
        """Uses a bulk UPDATE statement; result.rowcount is returned directly."""
        dao = DaoTask()
        db = _mock_session()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        db.execute = AsyncMock(return_value=mock_result)

        updated = await dao.bulk_update_status(db, [uuid4(), uuid4(), uuid4()], "done")

        assert updated == 3
        db.flush.assert_called_once()

    async def test_get_tasks_by_user_and_timerange_returns_list(self):
        dao = DaoTask()
        db = _mock_session()
        tasks = [_make_task() for _ in range(2)]
        db.execute = AsyncMock(return_value=_result_scalars_all(tasks))

        now = _now()
        result = await dao.get_tasks_by_user_and_timerange(
            db, uuid4(), now - timedelta(hours=1), now + timedelta(hours=1)
        )

        assert len(result) == 2

    # -- Observer custom methods --

    async def test_get_task_statistics_returns_status_count_dict(self):
        """Result rows have .status and .count attributes; DAO builds a dict."""
        dao = DaoTask()
        db = _mock_session()

        row_done = MagicMock()
        row_done.status = "done"
        row_done.count = 4
        row_pending = MagicMock()
        row_pending.status = "pending"
        row_pending.count = 1

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([row_done, row_pending]))
        db.execute = AsyncMock(return_value=mock_result)

        now = _now()
        stats = await dao.get_task_statistics(db, uuid4(), now - timedelta(days=7), now)

        assert stats["done"] == 4
        assert stats["pending"] == 1


# ── DaoConversation ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDaoConversation:
    async def test_has_no_delete_method(self):
        """Conversations are immutable audit records — delete is intentionally absent
        from both the protocol and the implementation."""
        assert not hasattr(DaoConversation(), "delete")

    async def test_create_returns_conversation_dto(self):
        dao = DaoConversation()
        db = _mock_session()
        user_id = uuid4()

        async def populate(obj):
            obj.id = uuid4()
            obj.created_at = _now()

        db.refresh = AsyncMock(side_effect=populate)

        result = await dao.create(
            db,
            ConversationCreateDTO(
                user_id=user_id,
                langgraph_thread_id="thread-abc",
                context_type="goal",
            ),
        )

        assert isinstance(result, ConversationDTO)
        assert result.context_type == "goal"

    async def test_get_by_id_not_found(self):
        dao = DaoConversation()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.get_by_id(db, uuid4()) is None

    async def test_update_applies_context_type(self):
        dao = DaoConversation()
        db = _mock_session()
        conv = _make_conversation(context_type="goal")
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(conv))
        db.refresh = AsyncMock()

        result = await dao.update(db, conv.id, ConversationUpdateDTO(context_type="reschedule"))

        assert result is not None
        assert result.context_type == "reschedule"

    async def test_update_not_found_returns_none(self):
        dao = DaoConversation()
        db = _mock_session()
        db.execute = AsyncMock(return_value=_result_scalar_one_or_none(None))

        assert await dao.update(db, uuid4(), ConversationUpdateDTO(context_type="task")) is None
