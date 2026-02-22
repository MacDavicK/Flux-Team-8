"""Unit tests for User DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.user import UserCreateDTO, UserUpdateDTO


class TestUserCreateDTO:
    def test_valid_user(self):
        dto = UserCreateDTO(email="alice@flux.ai")
        assert dto.email == "alice@flux.ai"
        assert dto.onboarded is False

    def test_empty_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateDTO(email="")

    def test_email_max_length_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateDTO(email=("x" * 256))

    def test_profile_and_notification_preferences_allowed(self):
        dto = UserCreateDTO(
            email="prefs@flux.ai",
            profile={"name": "Alice"},
            notification_preferences={"whatsapp_opted_in": True},
        )
        assert dto.profile == {"name": "Alice"}
        assert dto.notification_preferences == {"whatsapp_opted_in": True}


class TestUserUpdateDTO:
    def test_empty_update_allowed(self):
        dto = UserUpdateDTO()
        assert dto.email is None

    def test_partial_update(self):
        dto = UserUpdateDTO(onboarded=True)
        assert dto.onboarded is True
        assert dto.email is None

    def test_invalid_empty_email_rejected(self):
        with pytest.raises(ValidationError):
            UserUpdateDTO(email="")
