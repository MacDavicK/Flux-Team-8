"""Unit tests for NotificationLog DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from dao_service.schemas.notification_log import NotificationLogCreateDTO, NotificationLogUpdateDTO


class TestNotificationLogCreateDTO:
    def test_valid_channels(self):
        for channel in ["push", "whatsapp", "call"]:
            dto = NotificationLogCreateDTO(task_id=uuid4(), channel=channel)
            assert dto.channel == channel

    def test_invalid_channel_rejected(self):
        with pytest.raises(ValidationError):
            NotificationLogCreateDTO(task_id=uuid4(), channel="sms")


class TestNotificationLogUpdateDTO:
    def test_empty_update_allowed(self):
        dto = NotificationLogUpdateDTO()
        assert dto.channel is None

    def test_invalid_channel_rejected(self):
        with pytest.raises(ValidationError):
            NotificationLogUpdateDTO(channel="email")
