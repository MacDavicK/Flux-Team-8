"""Twilio Voice API service for phone call notifications."""

import os
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .models import CallRequest, CallResponse

logger = logging.getLogger(__name__)


class TwilioCallService:
    """Service class for managing Twilio voice calls."""
    
    def __init__(self):
        """Initialize Twilio client with credentials from environment."""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError(
                "Missing Twilio credentials. Set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables."
            )
        
        self.client = Client(self.account_sid, self.auth_token)
        logger.info("Twilio client initialized successfully")
    
    def initiate_call(self, call_request: CallRequest, base_url: str) -> CallResponse:
        """Initiate a phone call with TTS message and gather input.
        
        Args:
            call_request: Request containing phone number and task details
            base_url: Base URL for webhook callbacks
        
        Returns:
            CallResponse with call details
        
        Raises:
            TwilioRestException: If call initiation fails
        """
        try:
            # Build TwiML URL for call handling
            twiml_url = f"{base_url}/notifications/call/twiml"
            
            # Add task_id as query parameter if provided
            if call_request.task_id:
                twiml_url += f"?task_id={call_request.task_id}&task_title={call_request.task_title}"
            else:
                twiml_url += f"?task_title={call_request.task_title}"
            
            logger.info(
                f"Initiating call to {call_request.phone_number} "
                f"for task: {call_request.task_title}"
            )
            
            # Create the call
            call = self.client.calls.create(
                to=call_request.phone_number,
                from_=self.from_number,
                url=twiml_url,
                method="POST",
                status_callback=f"{base_url}/notifications/call/status",
                status_callback_event=["completed", "failed"],
                status_callback_method="POST"
            )
            
            logger.info(f"Call initiated successfully. SID: {call.sid}")
            
            return CallResponse(
                call_sid=call.sid,
                status=call.status,
                to=call.to,
                message=f"Call initiated successfully to {call.to}"
            )
            
        except TwilioRestException as e:
            logger.error(f"Failed to initiate call: {str(e)}")
            raise
    
    def get_call_status(self, call_sid: str) -> Optional[str]:
        """Get the current status of a call.
        
        Args:
            call_sid: Twilio Call SID
        
        Returns:
            Call status string or None if call not found
        """
        try:
            call = self.client.calls(call_sid).fetch()
            return call.status
        except TwilioRestException as e:
            logger.error(f"Failed to fetch call status: {str(e)}")
            return None
