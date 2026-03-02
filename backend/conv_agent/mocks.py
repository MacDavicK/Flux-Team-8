"""
Flux Conv Agent -- Mock Services

In-memory mocks for the DAO client, Deepgram token minting, and
data stores. Import these in tests to isolate the conv_agent
from all external dependencies.

Usage:
    from conv_agent.mocks import (
        MockDaoClient, mock_deepgram_token, patch_conv_agent
    )
"""

from __future__ import annotations

import copy
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import patch


# -- Mock DAO Client ---------------------------------------------------------


class MockDaoClient:
    """
    In-memory replacement for ConvAgentDaoClient.

    Pre-populated with sample data for testing:
      - users: one user with profile
      - tasks: two pending tasks for today
      - conversations, messages, goals: empty
    """

    def __init__(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._users: dict[str, dict] = {
            "mock-user-id": {
                "id": "mock-user-id",
                "email": "alex@test.com",
                "profile": {"name": "Alex", "chronotype": "morning"},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        self._tasks: dict[str, dict] = {
            "task-abc-123": {
                "id": "task-abc-123",
                "title": "Gym at 6pm",
                "scheduled_at": f"{today}T18:00:00Z",
                "trigger_type": "time",
                "status": "pending",
                "user_id": "mock-user-id",
            },
            "task-def-456": {
                "id": "task-def-456",
                "title": "Groceries at 5pm",
                "scheduled_at": f"{today}T17:00:00Z",
                "trigger_type": "time",
                "status": "pending",
                "user_id": "mock-user-id",
            },
        }
        self._conversations: dict[str, dict] = {}
        self._messages: dict[str, dict] = {}
        self._goals: dict[str, dict] = {}

    # -- Conversations -------------------------------------------------------

    async def create_conversation(
        self, user_id: str, langgraph_thread_id: str, context_type: str = "voice",
        voice_session_id: str | None = None,
    ) -> dict:
        conv_id = str(uuid.uuid4())
        conv = {
            "id": conv_id,
            "user_id": user_id,
            "langgraph_thread_id": langgraph_thread_id,
            "context_type": context_type,
            "voice_session_id": voice_session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_message_at": None,
            "extracted_intent": None,
            "intent_payload": None,
            "linked_goal_id": None,
            "linked_task_id": None,
            "ended_at": None,
            "duration_seconds": None,
        }
        self._conversations[conv_id] = conv
        return copy.deepcopy(conv)

    async def get_conversation(self, conversation_id: str) -> dict:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        return copy.deepcopy(conv)

    async def update_conversation_voice(
        self, conversation_id: str, **fields: Any
    ) -> dict:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        conv.update(fields)
        return copy.deepcopy(conv)

    # -- Messages ------------------------------------------------------------

    async def save_message(
        self, conversation_id: str, role: str, content: str,
        input_modality: str = "voice",
    ) -> dict:
        msg_id = str(uuid.uuid4())
        msg = {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "input_modality": input_modality,
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._messages[msg_id] = msg
        return copy.deepcopy(msg)

    async def get_messages(self, conversation_id: str) -> list[dict]:
        return [
            copy.deepcopy(m) for m in self._messages.values()
            if m["conversation_id"] == conversation_id
        ]

    async def count_messages(self, conversation_id: str) -> int:
        return sum(
            1 for m in self._messages.values()
            if m["conversation_id"] == conversation_id
        )

    # -- Users ---------------------------------------------------------------

    async def get_user(self, user_id: str) -> Optional[dict]:
        user = self._users.get(user_id)
        return copy.deepcopy(user) if user else None

    # -- Tasks ---------------------------------------------------------------

    async def get_today_tasks(
        self, user_id: str, start_at: str, end_at: str
    ) -> list[dict]:
        return [
            copy.deepcopy(t) for t in self._tasks.values()
            if t.get("user_id") == user_id
        ]

    async def get_task(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        return copy.deepcopy(task) if task else None

    async def update_task(self, task_id: str, **fields: Any) -> dict:
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        task.update(fields)
        return copy.deepcopy(task)

    async def create_task(
        self, user_id: str, title: str, trigger_type: str = "time", **fields: Any
    ) -> dict:
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "user_id": user_id,
            "title": title,
            "trigger_type": trigger_type,
            "status": "pending",
            **fields,
        }
        self._tasks[task_id] = task
        return copy.deepcopy(task)

    # -- Goals ---------------------------------------------------------------

    async def create_goal(
        self, user_id: str, title: str, target_weeks: int = 6,
        description: str = "",
    ) -> dict:
        goal_id = str(uuid.uuid4())
        goal = {
            "id": goal_id,
            "user_id": user_id,
            "title": title,
            "target_weeks": target_weeks,
            "description": description,
            "status": "active",
        }
        self._goals[goal_id] = goal
        return copy.deepcopy(goal)


# -- Mock Deepgram Token ----------------------------------------------------


async def mock_deepgram_token() -> str:
    """Return a fake Deepgram JWT token for testing."""
    return "MOCK_DEEPGRAM_TOKEN_FOR_TESTING"


# -- Legacy Supabase mocks (kept for reference / internal use) ---------------

class MockResponse:
    """Mimics the Supabase query response shape."""

    def __init__(self, data: Any = None, count: int | None = None):
        self.data = data if data is not None else []
        self.count = count


class MockSupabaseClient:
    """In-memory Supabase-style client (retained for backward compatibility)."""

    def __init__(self):
        self._store: dict[str, list[dict]] = {}

    def table(self, name: str):
        return self  # stub


# -- Patch Context Manager --------------------------------------------------


@contextmanager
def patch_conv_agent():
    """
    Context manager that patches all external dependencies used by conv_agent.

    Patches:
      - conv_agent.voice_service.get_dao_client -> MockDaoClient()
      - conv_agent.intent_handler.get_dao_client -> MockDaoClient()
      - conv_agent.voice_service.mint_deepgram_token -> mock token
    """
    mock_client = MockDaoClient()

    with (
        patch(
            "conv_agent.voice_service.get_dao_client",
            return_value=mock_client,
        ),
        patch(
            "conv_agent.intent_handler.get_dao_client",
            return_value=mock_client,
        ),
        patch(
            "conv_agent.voice_service.mint_deepgram_token",
            side_effect=mock_deepgram_token,
        ),
    ):
        yield mock_client
