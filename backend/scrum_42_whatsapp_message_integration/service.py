"""
WhatsApp messaging service using Twilio API
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .models import WhatsAppNotification, NotificationStatus


logger = logging.getLogger(__name__)


class WhatsAppServiceError(Exception):
    """Custom exception for WhatsApp service errors"""
    pass


class WhatsAppService:
    """Service for sending WhatsApp messages via Twilio"""
    
    def __init__(self):
        """Initialize Twilio client with credentials from environment"""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_from = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')  # Default sandbox number
        self.app_base_url = os.getenv('APP_BASE_URL', 'https://flux-life-assistant.app')
        
        if not self.account_sid or not self.auth_token:
            raise WhatsAppServiceError(
                "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in environment variables"
            )
        
        self.client = Client(self.account_sid, self.auth_token)
        logger.info("WhatsAppService initialized successfully")
    
    def format_message(self, task_title: str, task_id: str) -> tuple[str, str]:
        """
        Format the WhatsApp message with task details and app link
        
        Args:
            task_title: Title of the task
            task_id: ID of the task
            
        Returns:
            Tuple of (message_text, app_link)
        """
        app_link = f"{self.app_base_url}/tasks/{task_id}"
        message = f"Hey! Don't forget: {task_title} 🎯\n\n{app_link}"
        return message, app_link
    
    def send_message(
        self, 
        task_id: str,
        task_title: str,
        recipient_number: str,
        custom_message: Optional[str] = None
    ) -> WhatsAppNotification:
        """
        Send a WhatsApp message for a task reminder
        
        Args:
            task_id: ID of the task
            task_title: Title of the task
            recipient_number: Recipient's WhatsApp number (E.164 format)
            custom_message: Optional custom message (defaults to template)
            
        Returns:
            WhatsAppNotification object with send status
            
        Raises:
            WhatsAppServiceError: If message fails to send
        """
        # Ensure recipient number has whatsapp: prefix
        if not recipient_number.startswith('whatsapp:'):
            recipient_number = f'whatsapp:{recipient_number}'
        
        # Format message
        if custom_message:
            message_text = custom_message
            app_link = f"{self.app_base_url}/tasks/{task_id}"
        else:
            message_text, app_link = self.format_message(task_title, task_id)
        
        # Create notification object
        notification = WhatsAppNotification(
            task_id=task_id,
            task_title=task_title,
            recipient_number=recipient_number,
            message=message_text,
            app_link=app_link
        )
        
        try:
            # Send message via Twilio
            message = self.client.messages.create(
                body=message_text,
                from_=self.whatsapp_from,
                to=recipient_number
            )
            
            # Update notification with success details
            notification.status = NotificationStatus.SENT
            notification.message_sid = message.sid
            notification.sent_at = datetime.utcnow()
            
            logger.info(
                f"WhatsApp message sent successfully. "
                f"Task: {task_id}, MessageSID: {message.sid}, To: {recipient_number}"
            )
            
        except TwilioRestException as e:
            # Handle Twilio-specific errors
            error_msg = f"Twilio error: {e.msg} (Code: {e.code})"
            notification.status = NotificationStatus.FAILED
            notification.error_message = error_msg
            
            logger.error(
                f"Failed to send WhatsApp message. "
                f"Task: {task_id}, Error: {error_msg}, To: {recipient_number}"
            )
            
            # Re-raise as WhatsAppServiceError
            raise WhatsAppServiceError(error_msg) from e
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error: {str(e)}"
            notification.status = NotificationStatus.FAILED
            notification.error_message = error_msg
            
            logger.error(
                f"Unexpected error sending WhatsApp message. "
                f"Task: {task_id}, Error: {error_msg}, To: {recipient_number}"
            )
            
            raise WhatsAppServiceError(error_msg) from e
        
        return notification
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a sent message from Twilio
        
        Args:
            message_sid: Twilio message SID
            
        Returns:
            Dictionary with message status details
        """
        try:
            message = self.client.messages(message_sid).fetch()
            return {
                'sid': message.sid,
                'status': message.status,
                'date_sent': message.date_sent,
                'date_updated': message.date_updated,
                'error_code': message.error_code,
                'error_message': message.error_message
            }
        except TwilioRestException as e:
            logger.error(f"Failed to fetch message status: {e.msg}")
            raise WhatsAppServiceError(f"Failed to fetch message status: {e.msg}") from e
