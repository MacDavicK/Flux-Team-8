"""
WhatsApp Message Integration Module

This module provides functionality to send WhatsApp messages via Twilio API
for task reminders and notifications.
"""

from .routes import whatsapp_bp
from .service import WhatsAppService
from .models import WhatsAppNotification

__all__ = ['whatsapp_bp', 'WhatsAppService', 'WhatsAppNotification']
