"""
Shared fixtures for legacy app/ tests.

Uses real OpenRouter LLM calls (key loaded from backend/.env).
Mocks Supabase only since DB may not be running.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@pytest.fixture()
def mock_supabase():
    """
    Patch get_supabase_client in goal_service so no real DB calls happen.
    Returns the mock client so tests can configure return values.
    """
    with patch("app.services.goal_service.get_supabase_client") as mock_get_sb:
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        mock_result = MagicMock()
        mock_result.data = [{"id": "00000000-0000-0000-0000-000000000001"}]

        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = mock_result
        mock_table.update.return_value.eq.return_value.execute.return_value = mock_result
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

        mock_sb.table.return_value = mock_table
        yield mock_sb


@pytest.fixture()
def agent():
    """Fresh GoalPlannerAgent instance using real OpenRouter from .env."""
    from app.agents.goal_planner import GoalPlannerAgent
    return GoalPlannerAgent(conversation_id="test-conv-1", user_id="test-user-1")


@pytest.fixture()
def app_client(mock_supabase):
    """Sync FastAPI TestClient for legacy app/ tests (DB mocked, real OpenRouter)."""
    from app.main import app as legacy_app
    from app.routers.goals import _active_agents
    _active_agents.clear()
    return TestClient(legacy_app)
