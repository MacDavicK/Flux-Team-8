"""
21.3 — Shared pytest fixtures for Flux backend tests.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ─────────────────────────────────────────────────────────────────
# 21.3.3 — AsyncMock helpers for LLM call and Twilio client
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_call(monkeypatch):
    """Patch llm_call and validated_llm_call to return controllable values."""
    mock = AsyncMock(return_value='{"intent": "CLARIFY", "payload": {}, "clarification_question": "What goal?"}')
    monkeypatch.setattr("app.services.llm.llm_call", mock)
    monkeypatch.setattr("app.services.llm.validated_llm_call", AsyncMock())
    return mock


@pytest.fixture
def mock_twilio(monkeypatch):
    """Patch Twilio client methods."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(sid="SM_test_123")
    mock_client.calls.create.return_value = MagicMock(sid="CA_test_456")
    mock_client.verify.v2.services.return_value.verifications.create.return_value = MagicMock(status="pending")
    mock_client.verify.v2.services.return_value.verification_checks.create.return_value = MagicMock(status="approved")
    monkeypatch.setattr("app.services.twilio_service._client", mock_client)
    return mock_client


@pytest.fixture
def mock_db(monkeypatch):
    """Patch the db helper with AsyncMock methods."""
    mock = MagicMock()
    mock.fetch = AsyncMock(return_value=[])
    mock.fetchrow = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value="OK")
    mock.fetchval = AsyncMock(return_value=None)
    monkeypatch.setattr("app.services.supabase.db", mock)
    return mock
