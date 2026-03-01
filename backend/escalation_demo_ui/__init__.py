"""Escalation Demo UI Module

This module provides functionality for the escalation notification demo UI,
including API endpoints for triggering escalation flows with configurable speeds.
"""

from .routes import escalation_demo_bp
from .service import EscalationDemoService
from .models import EscalationEvent, NotificationStep

__all__ = ['escalation_demo_bp', 'EscalationDemoService', 'EscalationEvent', 'NotificationStep']