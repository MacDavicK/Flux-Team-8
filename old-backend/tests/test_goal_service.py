"""
Tests for the goal_service database operations.

All Supabase calls are mocked — these tests verify the service
constructs the right queries and handles responses correctly.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.schemas import PlanMilestone


class TestCreateConversation:
    def test_creates_conversation_and_returns_id(self, mock_supabase):
        from app.services.goal_service import create_conversation

        result_id = create_conversation(
            user_id="user-1",
            initial_state={"messages": [], "state": "IDLE"},
        )

        assert result_id == "00000000-0000-0000-0000-000000000001"
        mock_supabase.table.assert_called_with("conversations")

    def test_passes_correct_data(self, mock_supabase):
        from app.services.goal_service import create_conversation

        create_conversation(
            user_id="user-1",
            initial_state={"messages": [{"role": "user", "content": "hi"}]},
        )

        call_args = mock_supabase.table.return_value.insert.call_args
        inserted = call_args[0][0]
        assert inserted["user_id"] == "user-1"
        assert inserted["goal_id"] is None
        assert inserted["status"] == "open"


class TestCreateGoal:
    def test_creates_goal_and_returns_id(self, mock_supabase):
        from app.services.goal_service import create_goal

        goal_id = create_goal(
            user_id="user-1",
            title="Lose weight for wedding",
            category="health_fitness",
            timeline="March 15th",
        )

        assert goal_id == "00000000-0000-0000-0000-000000000001"
        mock_supabase.table.assert_called_with("goals")


class TestCreateMilestones:
    def test_creates_6_milestones(self, mock_supabase):
        from app.services.goal_service import create_milestones

        # Mock: return 6 rows with ids
        mock_result = MagicMock()
        mock_result.data = [{"id": f"ms-{i}"} for i in range(6)]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        milestones = [
            PlanMilestone(week=i + 1, title=f"Week {i + 1}", tasks=["task1", "task2"])
            for i in range(6)
        ]

        ids = create_milestones("goal-1", milestones)

        assert len(ids) == 6
        call_args = mock_supabase.table.return_value.insert.call_args
        rows = call_args[0][0]
        assert len(rows) == 6
        assert rows[0]["goal_id"] == "goal-1"
        assert rows[0]["week_number"] == 1


class TestCreateTasksFromPlan:
    def test_creates_tasks_for_all_milestones(self, mock_supabase):
        from app.services.goal_service import create_tasks_from_plan

        milestones = [
            PlanMilestone(week=1, title="Week 1", tasks=["Walk", "Meal prep", "Cardio"]),
            PlanMilestone(week=2, title="Week 2", tasks=["Gym", "Diet"]),
        ]
        milestone_ids = ["ms-1", "ms-2"]

        # Mock: return task rows
        mock_result = MagicMock()
        mock_result.data = [{"id": f"task-{i}"} for i in range(5)]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        task_ids = create_tasks_from_plan(
            user_id="user-1",
            goal_id="goal-1",
            milestones=milestones,
            milestone_ids=milestone_ids,
            start_date=datetime(2026, 2, 14),
        )

        assert len(task_ids) == 5
        call_args = mock_supabase.table.return_value.insert.call_args
        rows = call_args[0][0]
        assert len(rows) == 5
        assert all(r["user_id"] == "user-1" for r in rows)
        assert all(r["goal_id"] == "goal-1" for r in rows)
        assert all(r["is_recurring"] is True for r in rows)

    def test_empty_plan_returns_empty(self, mock_supabase):
        from app.services.goal_service import create_tasks_from_plan

        task_ids = create_tasks_from_plan(
            user_id="user-1",
            goal_id="goal-1",
            milestones=[],
            milestone_ids=[],
        )
        assert task_ids == []


class TestSaveCompletePlan:
    def test_creates_goal_milestones_tasks_and_links(self, mock_supabase):
        from app.services.goal_service import save_complete_plan

        # Mock sequential calls — each table().insert().execute() returns ids
        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "goals":
                mock_result = MagicMock()
                mock_result.data = [{"id": "goal-99"}]
                mock_table.insert.return_value.execute.return_value = mock_result
            elif name == "milestones":
                mock_result = MagicMock()
                mock_result.data = [{"id": f"ms-{i}"} for i in range(6)]
                mock_table.insert.return_value.execute.return_value = mock_result
            elif name == "tasks":
                mock_result = MagicMock()
                mock_result.data = [{"id": f"task-{i}"} for i in range(20)]
                mock_table.insert.return_value.execute.return_value = mock_result
            elif name == "conversations":
                mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        milestones = [
            PlanMilestone(week=i + 1, title=f"Week {i + 1}", tasks=["t1", "t2", "t3"])
            for i in range(6)
        ]

        result = save_complete_plan(
            user_id="user-1",
            conversation_id="conv-1",
            agent_context={"goal": "Lose weight", "timeline": "March 15th"},
            milestones=milestones,
        )

        assert result["goal_id"] == "goal-99"
        assert len(result["milestone_ids"]) == 6
        assert len(result["task_ids"]) == 20
