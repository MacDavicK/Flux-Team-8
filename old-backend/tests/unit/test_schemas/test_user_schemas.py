"""Unit tests for User DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.user import UserCreateDTO, UserUpdateDTO


class TestUserCreateDTO:
    def test_valid_user(self):
        dto = UserCreateDTO(name="Alice", email="alice@flux.ai")
        assert dto.name == "Alice"
        assert dto.preferences == {}
        assert dto.demo_mode is False

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateDTO(name="", email="alice@flux.ai")

    def test_empty_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreateDTO(name="Alice", email="")

    def test_name_exceeds_max_length(self):
        with pytest.raises(ValidationError):
            UserCreateDTO(name="x" * 256, email="alice@flux.ai")

    def test_custom_preferences(self):
        dto = UserCreateDTO(
            name="Bob",
            email="bob@flux.ai",
            preferences={"theme": "dark", "notifications": True},
        )
        assert dto.preferences["theme"] == "dark"


class TestUserUpdateDTO:
    def test_empty_update_allowed(self):
        dto = UserUpdateDTO()
        assert dto.name is None
        assert dto.email is None

    def test_partial_update(self):
        dto = UserUpdateDTO(name="Updated Name")
        assert dto.name == "Updated Name"
        assert dto.email is None

    def test_empty_name_rejected_on_update(self):
        with pytest.raises(ValidationError):
            UserUpdateDTO(name="")
