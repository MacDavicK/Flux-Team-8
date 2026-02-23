"""Phone Call Trigger Module for Notification Escalation.

This module provides Twilio Voice API integration for making
phone calls with TTS messages and gathering user acknowledgments.

SCRUM-43: Phone Call Trigger
Owner: BE-B
Points: 3
Component: notifications
"""

__version__ = "1.0.0"

from .routes import router
from .models import CallRequest, CallResponse, GatherResponse
from .service import TwilioCallService

__all__ = [
    "router",
    "CallRequest",
    "CallResponse",
    "GatherResponse",
    "TwilioCallService",
]
