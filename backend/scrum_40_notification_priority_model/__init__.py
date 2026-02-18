"""
Notification Priority Model API

This module provides the API for managing notification priorities and escalation rules.
It determines the escalation path based on priority levels (standard/important/must-not-miss)
and applies escalation speed multipliers from demo flags.
"""

from .routes import priority_router

__all__ = ['priority_router']
