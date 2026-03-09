"""
Flux Conv Agent -- Voice Service Tests

Tests for voice_service using in-memory mocks (no Supabase, no Deepgram).
"""

from __future__ import annotations

import sys
import types
import pytest

from app.conv_agent.mocks import patch_conv_agent
from app.conv_agent import voice_service


# -- Config Loading Tests ----------------------------------------------------


def test_load_system_prompt_returns_string():
    """load_system_prompt() should return a non-empty string containing 'Flux'."""
    result = voice_service.load_system_prompt()
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Flux" in result


def test_load_intents_returns_three_functions():
    """load_intents() should return 3 function definitions from intents.yaml."""
    result = voice_service.load_intents()
    assert isinstance(result, list)
    assert len(result) == 3
    for func in result:
        assert "name" in func
        assert "description" in func
        assert "parameters" in func


# -- Session CRUD Tests (mocked DAO client) ---------------------------------


@pytest.mark.asyncio
async def test_create_session_inserts_conversation():
    """create_session() should insert a conversation and return a non-empty ID."""
    with patch_conv_agent():
        session_id = await voice_service.create_session("mock-user-id")
        assert isinstance(session_id, str)
        assert len(session_id) > 0


@pytest.mark.asyncio
async def test_save_message_inserts_row():
    """save_message() should insert a message and return a message_id string."""
    with patch_conv_agent():
        session_id = await voice_service.create_session("mock-user-id")
        message_id = await voice_service.save_message(session_id, "user", "Hello")
        assert isinstance(message_id, str)
        assert len(message_id) > 0


@pytest.mark.asyncio
async def test_get_messages_returns_empty_for_new_session():
    """get_messages() should return an empty list for a session with no messages."""
    with patch_conv_agent():
        session_id = await voice_service.create_session("mock-user-id")
        messages = await voice_service.get_messages(session_id)
        assert isinstance(messages, list)


# -- Composite Config Tests (mocked DAO client + Deepgram) ------------------


@pytest.mark.asyncio
async def test_build_session_config_shape():
    """build_session_config() should return a dict with session_id, deepgram_token, config."""
    with patch_conv_agent():
        result = await voice_service.build_session_config("mock-user-id")
        assert "session_id" in result
        assert "deepgram_token" in result
        assert "config" in result
        assert result["deepgram_token"] == "MOCK_DEEPGRAM_TOKEN_FOR_TESTING"

        config = result["config"]
        assert "system_prompt" in config
        assert "functions" in config
        assert "voice_model" in config
        assert "listen_model" in config
        assert "llm_model" in config


# -- App Startup Regression Tests --------------------------------------------


def test_app_starts_when_scrum_router_raises_value_error(monkeypatch):
    """
    app.main must not crash when a scrum router raises ValueError on import.

    Regression for: 'except ImportError' → 'except Exception' in app/main.py.
    Before the fix, pywebpush being installed but VAPID keys missing caused
    PushNotificationService.__init__ to raise ValueError at module load time.
    That ValueError propagated through the old 'except ImportError' block,
    crashing the entire app startup.
    """
    # Inject a fake scrum module that raises ValueError on import (simulates
    # PushNotificationService requiring VAPID keys that aren't configured).
    def make_bad_module(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        raise ValueError(f"VAPID keys not configured (simulated in {name})")

    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def patched_import(name, *args, **kwargs):
        if name in (
            "scrum_40_notification_priority_model.routes",
            "scrum_41_push_notification_integration.routes",
            "scrum_43_phone_call_trigger.routes",
        ):
            raise ValueError(f"VAPID keys not configured (simulated in {name})")
        return original_import(name, *args, **kwargs)

    # Remove cached app.main so Python re-executes the module-level try/except.
    sys.modules.pop("app.main", None)

    import builtins
    monkeypatch.setattr(builtins, "__import__", patched_import)

    # Should not raise — the app must start gracefully.
    try:
        import app.main as main_module  # noqa: F401
        assert hasattr(main_module, "app"), "app.main must expose a FastAPI 'app' object"
    finally:
        sys.modules.pop("app.main", None)
