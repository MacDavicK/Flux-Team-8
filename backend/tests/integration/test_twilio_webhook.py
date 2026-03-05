"""
21.2.4 — Integration tests for Twilio webhook signature validation.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def app_client():
    """Create test client with minimal app."""
    from fastapi import FastAPI
    from app.api.v1.webhooks import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_invalid_signature_returns_403(app_client):
    """Requests with invalid Twilio signature are rejected with 403."""
    with patch("app.api.v1.webhooks.RequestValidator") as mock_validator_cls:
        mock_validator = MagicMock()
        mock_validator.validate.return_value = False
        mock_validator_cls.return_value = mock_validator

        response = app_client.post(
            "/webhooks/twilio/whatsapp",
            data={"Body": "1", "MessageSid": "SM123", "WaId": "+1234567890"},
            headers={"X-Twilio-Signature": "invalid"},
        )

    assert response.status_code == 403


def test_valid_signature_processes_whatsapp(app_client):
    """Requests with valid Twilio signature are processed (not 403)."""
    with patch("app.api.v1.webhooks.RequestValidator") as mock_validator_cls, \
         patch("app.api.v1.webhooks.db") as mock_db:

        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_validator_cls.return_value = mock_validator

        mock_db.fetchrow = AsyncMock(side_effect=[
            None,  # idempotency check — no existing log
            {"id": "user-1"},  # user lookup
            {"task_id": "task-1"},  # task lookup
        ])
        mock_db.execute = AsyncMock(return_value="OK")

        response = app_client.post(
            "/webhooks/twilio/whatsapp",
            data={"Body": "1", "MessageSid": "SM123", "WaId": "+1234567890"},
            headers={"X-Twilio-Signature": "valid"},
        )

    assert response.status_code != 403
