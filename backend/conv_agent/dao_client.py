"""
Flux Conv Agent -- DAO Service HTTP Client

Wraps all HTTP calls from the conv_agent to the dao_service REST API.
Constructor accepts an optional httpx.AsyncClient for test injection.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from conv_agent.config import settings

logger = logging.getLogger(__name__)


class ConvAgentDaoClient:
    """HTTP client for the dao_service REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        service_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or settings.dao_service_url).rstrip("/")
        self.service_key = service_key or settings.dao_service_key
        self._external_client = client
        self._headers = {"X-Flux-Service-Key": self.service_key}

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute an HTTP request, using injected or fresh client."""
        url = f"{self.base_url}{path}"
        if self._external_client is not None:
            resp = await self._external_client.request(
                method, url, headers=self._headers, **kwargs
            )
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method, url, headers=self._headers, **kwargs
                )
        resp.raise_for_status()
        return resp

    # -- Conversations -------------------------------------------------------

    async def create_conversation(
        self, user_id: str, langgraph_thread_id: str, context_type: str = "voice",
        voice_session_id: str | None = None,
    ) -> dict:
        """POST /api/v1/conversations/"""
        payload: dict[str, Any] = {
            "user_id": user_id,
            "langgraph_thread_id": langgraph_thread_id,
            "context_type": context_type,
        }
        if voice_session_id:
            payload["voice_session_id"] = voice_session_id
        resp = await self._request("POST", "/api/v1/conversations/", json=payload)
        return resp.json()

    async def get_conversation(self, conversation_id: str) -> dict:
        """GET /api/v1/conversations/{conversation_id}"""
        resp = await self._request("GET", f"/api/v1/conversations/{conversation_id}")
        return resp.json()

    async def update_conversation_voice(
        self, conversation_id: str, **fields: Any
    ) -> dict:
        """PATCH /api/v1/conversations/{conversation_id}/voice"""
        resp = await self._request(
            "PATCH", f"/api/v1/conversations/{conversation_id}/voice", json=fields
        )
        return resp.json()

    # -- Messages ------------------------------------------------------------

    async def save_message(
        self, conversation_id: str, role: str, content: str,
        input_modality: str = "voice",
    ) -> dict:
        """POST /api/v1/messages/"""
        resp = await self._request("POST", "/api/v1/messages/", json={
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "input_modality": input_modality,
        })
        return resp.json()

    async def get_messages(self, conversation_id: str) -> list[dict]:
        """GET /api/v1/messages/?conversation_id={conversation_id}"""
        resp = await self._request(
            "GET", "/api/v1/messages/", params={"conversation_id": conversation_id}
        )
        return resp.json()

    async def count_messages(self, conversation_id: str) -> int:
        """Count messages by fetching the list and returning its length."""
        messages = await self.get_messages(conversation_id)
        return len(messages)

    # -- Users ---------------------------------------------------------------

    async def get_user(self, user_id: str) -> Optional[dict]:
        """GET /api/v1/users/{user_id} -- returns None on 404."""
        try:
            resp = await self._request("GET", f"/api/v1/users/{user_id}")
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    # -- Tasks ---------------------------------------------------------------

    async def get_today_tasks(
        self, user_id: str, start_at: str, end_at: str
    ) -> list[dict]:
        """GET /api/v1/tasks/by-timerange -- returns [] on error."""
        try:
            resp = await self._request(
                "GET", "/api/v1/tasks/by-timerange",
                params={"user_id": user_id, "start_at": start_at, "end_at": end_at},
            )
            return resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch tasks: %s", exc)
            return []

    async def get_task(self, task_id: str) -> Optional[dict]:
        """GET /api/v1/tasks/{task_id} -- returns None on 404."""
        try:
            resp = await self._request("GET", f"/api/v1/tasks/{task_id}")
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def update_task(self, task_id: str, **fields: Any) -> dict:
        """PATCH /api/v1/tasks/{task_id}"""
        resp = await self._request(
            "PATCH", f"/api/v1/tasks/{task_id}", json=fields
        )
        return resp.json()

    async def create_task(
        self, user_id: str, title: str, trigger_type: str = "time", **fields: Any
    ) -> dict:
        """POST /api/v1/tasks/"""
        payload = {
            "user_id": user_id,
            "title": title,
            "trigger_type": trigger_type,
            "status": "pending",
            **fields,
        }
        resp = await self._request("POST", "/api/v1/tasks/", json=payload)
        return resp.json()

    # -- Goals ---------------------------------------------------------------

    async def create_goal(
        self, user_id: str, title: str, target_weeks: int = 6,
        description: str = "",
    ) -> dict:
        """POST /api/v1/goals/"""
        resp = await self._request("POST", "/api/v1/goals/", json={
            "user_id": user_id,
            "title": title,
            "target_weeks": target_weeks,
            "description": description,
            "status": "active",
        })
        return resp.json()


def get_dao_client() -> ConvAgentDaoClient:
    """Module-level factory for the DAO client."""
    return ConvAgentDaoClient()
