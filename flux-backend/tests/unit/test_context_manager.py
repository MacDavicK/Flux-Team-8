"""
21.1.7 — Unit tests for window_conversation_history.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


def _make_history(n: int) -> list[dict]:
    """Create n alternating user/assistant messages."""
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"}
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_no_windowing_below_limits():
    """History under both limits is returned unchanged."""
    history = _make_history(5)
    with patch("app.config.settings") as mock_settings:
        mock_settings.max_conversation_messages = 20
        mock_settings.max_conversation_tokens = 8000
        from app.services.context_manager import window_conversation_history
        result = await window_conversation_history(history, "user-1")
    assert result == history


@pytest.mark.asyncio
async def test_summarization_triggers_at_message_limit():
    """When len(history) > max_conversation_messages, summarization is triggered."""
    history = _make_history(22)  # exceeds limit of 20

    mock_summary = "Summary of earlier messages."

    with patch("app.services.context_manager.settings") as mock_settings, \
         patch("app.services.context_manager.llm_call", AsyncMock(return_value=mock_summary)), \
         patch("app.services.context_manager.db"):
        mock_settings.max_conversation_messages = 20
        mock_settings.max_conversation_tokens = 8000

        from importlib import reload
        import app.services.context_manager as cm_module
        reload(cm_module)

        result = await cm_module.window_conversation_history(history, "user-1")

    # Summary message should be prepended
    assert result[0]["role"] == "summary"
    assert len(result) < len(history)


@pytest.mark.asyncio
async def test_summary_is_prepended_correctly():
    """The summary message is the first element; recent messages follow."""
    history = _make_history(30)
    mock_summary = "Condensed context."

    with patch("app.services.context_manager.settings") as mock_settings, \
         patch("app.services.context_manager.llm_call", AsyncMock(return_value=mock_summary)), \
         patch("app.services.context_manager.db"):
        mock_settings.max_conversation_messages = 20
        mock_settings.max_conversation_tokens = 8000

        from importlib import reload
        import app.services.context_manager as cm_module
        reload(cm_module)

        result = await cm_module.window_conversation_history(history, "user-1")

    assert result[0] == {"role": "summary", "content": mock_summary}
    # Recent half messages are preserved after summary
    midpoint = len(history) // 2
    recent = history[midpoint:]
    assert result[1:] == recent
