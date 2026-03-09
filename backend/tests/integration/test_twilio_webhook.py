"""
21.2.4 — Integration tests for Twilio webhook signature validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def _form_headers(signature: str) -> dict:
    return {
        "X-Twilio-Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }


_FORM_BODY = b"Body=1&MessageSid=SM123&WaId=%2B1234567890"


def _make_app():
    from fastapi import FastAPI
    from app.api.v1.webhooks import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_invalid_signature_returns_403():
    """Requests with invalid Twilio signature are rejected with 403."""
    client = _make_app()
    with patch("app.api.v1.webhooks.RequestValidator") as mock_validator_cls:
        mock_validator = MagicMock()
        mock_validator.validate.return_value = False
        mock_validator_cls.return_value = mock_validator

        response = client.post(
            "/webhooks/twilio/whatsapp",
            content=_FORM_BODY,
            headers=_form_headers("invalid"),
        )

    assert response.status_code == 403


def test_valid_signature_processes_whatsapp():
    """Requests with valid Twilio signature are processed (not 403)."""
    client = _make_app()
    with (
        patch("app.api.v1.webhooks.RequestValidator") as mock_validator_cls,
        patch("app.api.v1.webhooks.db") as mock_db,
    ):
        mock_validator = MagicMock()
        mock_validator.validate.return_value = True
        mock_validator_cls.return_value = mock_validator

        mock_db.fetchrow = AsyncMock(
            side_effect=[
                None,  # idempotency check — no existing log
                {"id": "user-1"},  # user lookup
                {"task_id": "task-1"},  # task lookup
            ]
        )
        mock_db.execute = AsyncMock(return_value="OK")

        response = client.post(
            "/webhooks/twilio/whatsapp",
            content=_FORM_BODY,
            headers=_form_headers("valid"),
        )

    assert response.status_code != 403
