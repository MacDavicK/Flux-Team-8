"""
Flux Conv Agent -- Voice Service

Handles Deepgram token minting, voice session lifecycle, message
persistence, and system prompt / intent loading.  All DB operations
route through the dao_service HTTP API via ConvAgentDaoClient.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.config import settings
from app.conv_agent.dao_client import get_dao_client

logger = logging.getLogger(__name__)


# -- Token Minting ----------------------------------------------------------


async def mint_deepgram_token() -> str:
    """
    Request a short-lived JWT from Deepgram's auth/grant endpoint.

    Returns the temporary access token string.
    Raises httpx.HTTPStatusError on failure.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.deepgram.com/v1/auth/grant",
            headers={"Authorization": f"Token {settings.deepgram_api_key}"},
            json={"time_to_live_in_seconds": settings.deepgram_token_ttl},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["access_token"]


# -- Config Loading ---------------------------------------------------------


def load_system_prompt() -> str:
    """
    Read the voice agent system prompt from the configured markdown file.

    Returns the raw markdown string.
    """
    prompt_path = Path(settings.voice_prompt_file)
    if not prompt_path.is_absolute():
        # Resolve relative to project root (three levels up from this file)
        prompt_path = Path(__file__).resolve().parents[3] / prompt_path
    return prompt_path.read_text(encoding="utf-8")


def load_intents() -> list[dict[str, Any]]:
    """
    Read intent definitions from the YAML config and convert them
    into Deepgram-compatible function objects.

    Each function object has: name, description, parameters (JSON Schema).
    """
    intents_path = Path(settings.voice_intents_file)
    if not intents_path.is_absolute():
        intents_path = Path(__file__).resolve().parents[3] / intents_path

    raw = yaml.safe_load(intents_path.read_text(encoding="utf-8"))
    functions: list[dict[str, Any]] = []

    for intent in raw.get("intents", []):
        # Build a JSON-Schema-style parameters object
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in intent.get("parameters", []):
            prop: dict[str, Any] = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }
            if "enum" in param:
                prop["enum"] = param["enum"]
            properties[param["name"]] = prop
            if param.get("required"):
                required.append(param["name"])

        functions.append({
            "name": intent["name"],
            "description": intent.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })

    return functions


# -- User Context -----------------------------------------------------------


async def _load_user_context(user_id: str) -> str:
    """Fetch user profile + today's tasks via dao_service and format as a prompt context block."""
    dao_client = get_dao_client()

    try:
        user = await dao_client.get_user(user_id)
        profile = (user or {}).get("profile") or {}
    except Exception as exc:
        logger.warning("Failed to load user profile: %s", exc)
        profile = {}

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_at = f"{today_str}T00:00:00Z"
    end_at = f"{today_str}T23:59:59Z"

    tasks = await dao_client.get_today_tasks(user_id, start_at, end_at)

    lines = ["\n\n---\n## Injected User Context"]
    lines.append(f"- Name: {profile.get('name', 'there')}")
    for key in ("chronotype", "work_hours", "sleep_window"):
        if profile.get(key):
            lines.append(f"- {key.replace('_', ' ').title()}: {profile[key]}")
    if tasks:
        lines.append("\n### Today's active tasks:")
        for t in tasks:
            tid = t.get("id", "")[:8]
            lines.append(f"- [{tid}] {t['title']} (at {t.get('scheduled_at', 'unscheduled')})")
    else:
        lines.append("\n### Today's active tasks: none")
    return "\n".join(lines)


# -- Session CRUD -----------------------------------------------------------


async def create_session(user_id: str) -> str:
    """
    Insert a new conversation row with context_type='voice' via dao_service.

    Uses a generated voice-prefixed value for the required
    langgraph_thread_id column (voice sessions don't use LangGraph).

    Returns the conversation ID (UUID string).
    Raises ValueError if the user_id does not exist in the database.
    """
    dao_client = get_dao_client()

    # Validate the user exists before attempting to create the conversation.
    # This surfaces a clear ValueError (→ 500 with a readable message) instead
    # of a cryptic 409 Conflict from the FK constraint violation.
    user = await dao_client.get_user(user_id)
    if user is None:
        raise ValueError(
            f"User '{user_id}' not found in the database. "
            "Ensure the seed data has been applied (supabase/scripts/seed_test_data.sql) "
            "or use a valid user ID."
        )

    session_id = str(uuid.uuid4())
    voice_thread_id = f"voice-{session_id}"

    result = await dao_client.create_conversation(
        user_id=user_id,
        langgraph_thread_id=voice_thread_id,
        context_type="voice",
        voice_session_id=session_id,
    )
    return result["id"]


async def close_session(session_id: str) -> int:
    """
    Mark a voice session as ended and return the message count.

    Sets ended_at to now and computes duration_seconds from created_at.
    """
    dao_client = get_dao_client()
    now = datetime.now(timezone.utc)

    # Get session to compute duration
    conv = await dao_client.get_conversation(session_id)
    created_str = conv.get("created_at", "")
    try:
        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        duration = int((now - created).total_seconds())
    except (ValueError, TypeError):
        duration = 0

    # Update the session with voice-specific fields
    await dao_client.update_conversation_voice(
        session_id, ended_at=now.isoformat(), duration_seconds=duration
    )

    # Count messages
    count = await dao_client.count_messages(session_id)
    return count


# -- Message Persistence ----------------------------------------------------


async def save_message(session_id: str, role: str, content: str) -> str:
    """
    Insert a single message row linked to the session via dao_service.

    Returns the message ID (UUID string).
    """
    dao_client = get_dao_client()
    result = await dao_client.save_message(session_id, role, content, "voice")
    return result["id"]


async def get_messages(session_id: str) -> list[dict]:
    """
    Retrieve all messages for a session, ordered chronologically.

    Returns a list of dicts with id, role, content, created_at.
    """
    dao_client = get_dao_client()
    return await dao_client.get_messages(session_id)


# -- Composite: Build Full Session Config -----------------------------------


async def build_session_config(user_id: str) -> dict[str, Any]:
    """
    Orchestrate session creation:
      1. Create conversation row via dao_service
      2. Mint Deepgram token
      3. Load system prompt + user context
      4. Load intent function definitions
      5. Return everything the frontend needs

    Returns a dict matching CreateSessionResponse shape.
    """
    session_id = await create_session(user_id)
    token = await mint_deepgram_token()

    # Build enriched system prompt
    base_prompt = load_system_prompt()
    user_context = await _load_user_context(user_id)
    full_prompt = base_prompt + user_context

    # Load function definitions
    functions = load_intents()

    return {
        "session_id": session_id,
        "deepgram_token": token,
        "config": {
            "system_prompt": full_prompt,
            "functions": functions,
            "voice_model": settings.deepgram_voice_model,
            "listen_model": settings.deepgram_listen_model,
            "llm_model": settings.deepgram_llm_model,
            "greeting": "Hey! What can I help you with today?",
        },
    }
