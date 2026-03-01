"""
Tests for the Goals API endpoints.

Uses FastAPI's TestClient with mocked DB, real OpenRouter calls via .env key.
"""

import pytest

from app.models.schemas import ConversationState


# ── POST /goals/start ──────────────────────────────────────

class TestStartGoal:
    def test_start_returns_200(self, app_client):
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        assert resp.status_code == 200

    def test_start_returns_conversation_id(self, app_client):
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        data = resp.json()
        assert "conversation_id" in data
        assert data["conversation_id"]  # non-empty

    def test_start_returns_gathering_timeline_state(self, app_client):
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        data = resp.json()
        assert data["state"] == ConversationState.GATHERING_TIMELINE

    def test_start_returns_ai_message(self, app_client):
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        data = resp.json()
        assert data["message"]  # non-empty string

    def test_start_non_fitness_stays_idle(self, app_client):
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to learn how to play piano",
        })
        data = resp.json()
        assert data["state"] == ConversationState.IDLE

    def test_start_missing_user_id_returns_422(self, app_client):
        resp = app_client.post("/goals/start", json={
            "message": "I want to lose weight",
        })
        assert resp.status_code == 422

    def test_start_missing_message_returns_422(self, app_client):
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
        })
        assert resp.status_code == 422


# ── POST /goals/{id}/respond ──────────────────────────────

class TestRespondToGoal:
    def _start_conversation(self, app_client):
        """Helper: start a conversation and return the conversation_id."""
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        return resp.json()["conversation_id"]

    def test_respond_advances_state(self, app_client):
        conv_id = self._start_conversation(app_client)
        resp = app_client.post(f"/goals/{conv_id}/respond", json={
            "message": "March 15th",
        })
        assert resp.status_code == 200
        assert resp.json()["state"] == ConversationState.GATHERING_CURRENT_STATE

    def test_respond_returns_ai_message(self, app_client):
        conv_id = self._start_conversation(app_client)
        resp = app_client.post(f"/goals/{conv_id}/respond", json={
            "message": "March 15th",
        })
        assert resp.json()["message"]

    def test_respond_unknown_conversation_returns_404(self, app_client):
        resp = app_client.post("/goals/nonexistent-id/respond", json={
            "message": "March 15th",
        })
        assert resp.status_code == 404

    def test_respond_missing_message_returns_422(self, app_client):
        conv_id = self._start_conversation(app_client)
        resp = app_client.post(f"/goals/{conv_id}/respond", json={})
        assert resp.status_code == 422

    def test_full_flow_via_api(self, app_client):
        """Walk through the entire conversation via API endpoints."""
        # Start
        r1 = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        conv_id = r1.json()["conversation_id"]
        assert r1.json()["state"] == ConversationState.GATHERING_TIMELINE

        # Timeline
        r2 = app_client.post(f"/goals/{conv_id}/respond", json={"message": "March 15th"})
        assert r2.json()["state"] == ConversationState.GATHERING_CURRENT_STATE

        # Current state
        r3 = app_client.post(f"/goals/{conv_id}/respond", json={"message": "85 kg"})
        assert r3.json()["state"] == ConversationState.GATHERING_TARGET

        # Target
        r4 = app_client.post(f"/goals/{conv_id}/respond", json={"message": "75 kg"})
        assert r4.json()["state"] == ConversationState.GATHERING_PREFERENCES

        # Preferences → plan generated
        r5 = app_client.post(f"/goals/{conv_id}/respond", json={"message": "Gym and diet"})
        assert r5.json()["state"] == ConversationState.AWAITING_CONFIRMATION
        assert r5.json()["plan"] is not None
        assert len(r5.json()["plan"]) == 6

        # Confirm
        r6 = app_client.post(f"/goals/{conv_id}/respond", json={"message": "Looks good!"})
        assert r6.json()["state"] == ConversationState.CONFIRMED


# ── GET /goals/{id} ─────────────────────────────────────────

class TestGetConversation:
    def test_get_existing_conversation(self, app_client):
        # Start one first
        resp = app_client.post("/goals/start", json={
            "user_id": "test-user-1",
            "message": "I want to lose weight for a wedding",
        })
        conv_id = resp.json()["conversation_id"]

        # Now GET it
        get_resp = app_client.get(f"/goals/{conv_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["conversation_id"] == conv_id
        assert get_resp.json()["state"] == ConversationState.GATHERING_TIMELINE

    def test_get_nonexistent_returns_404(self, app_client):
        resp = app_client.get("/goals/does-not-exist")
        assert resp.status_code == 404


# ── Health Check ────────────────────────────────────────────

class TestHealthCheck:
    def test_health_returns_ok(self, app_client):
        resp = app_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
