"""Service layer for escalation demo logic"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from .models import (
    EscalationEvent,
    NotificationStep,
    NotificationChannel,
    NotificationStatus,
    EscalationSpeed
)

logger = logging.getLogger(__name__)


class EscalationDemoService:
    """Service for managing escalation notification demos"""

    def __init__(self):
        # In-memory storage for demo purposes
        # In production, this would use a database
        self.active_escalations: Dict[str, EscalationEvent] = {}
        self.escalation_tasks: Dict[str, asyncio.Task] = {}

    async def create_escalation(self, 
                                user_id: str,
                                title: str,
                                message: str,
                                speed: EscalationSpeed = EscalationSpeed.NORMAL) -> EscalationEvent:
        """Create and start a new escalation event"""
        escalation_id = str(uuid.uuid4())
        
        escalation = EscalationEvent(
            id=escalation_id,
            user_id=user_id,
            title=title,
            message=message,
            speed=speed
        )
        
        self.active_escalations[escalation_id] = escalation
        
        # Start the escalation flow asynchronously
        task = asyncio.create_task(self._execute_escalation_flow(escalation))
        self.escalation_tasks[escalation_id] = task
        
        logger.info(f"Created escalation {escalation_id} with speed {speed.value}")
        return escalation

    async def _execute_escalation_flow(self, escalation: EscalationEvent):
        """Execute the escalation flow through all steps"""
        try:
            for step in escalation.steps:
                if escalation.is_acknowledged:
                    logger.info(f"Escalation {escalation.id} acknowledged, stopping flow")
                    break
                
                # Calculate adjusted delay based on speed multiplier
                adjusted_delay = escalation.get_adjusted_delay(step.delay_seconds)
                
                if adjusted_delay > 0:
                    logger.info(f"Waiting {adjusted_delay}s before {step.channel.value}")
                    await asyncio.sleep(adjusted_delay)
                
                # Check again if acknowledged during sleep
                if escalation.is_acknowledged:
                    break
                
                # Execute the notification step
                await self._send_notification(escalation, step)
                
                # Advance to next step
                escalation.advance_step()
            
            logger.info(f"Escalation {escalation.id} completed")
            
        except asyncio.CancelledError:
            logger.info(f"Escalation {escalation.id} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in escalation flow {escalation.id}: {e}")
            escalation.is_complete = True

    async def _send_notification(self, 
                                 escalation: EscalationEvent, 
                                 step: NotificationStep):
        """Send notification for a specific step"""
        logger.info(f"Sending {step.channel.value} notification for {escalation.id}")
        
        step.status = NotificationStatus.SENT
        step.sent_at = datetime.utcnow()
        
        try:
            # Simulate notification sending
            # In production, this would call actual notification services
            if step.channel == NotificationChannel.PUSH:
                await self._send_push_notification(escalation, step)
            elif step.channel == NotificationChannel.WHATSAPP:
                await self._send_whatsapp_notification(escalation, step)
            elif step.channel == NotificationChannel.PHONE_CALL:
                await self._send_phone_call(escalation, step)
            
            step.status = NotificationStatus.DELIVERED
            step.delivered_at = datetime.utcnow()
            logger.info(f"Successfully sent {step.channel.value} notification")
            
        except Exception as e:
            step.status = NotificationStatus.FAILED
            step.error_message = str(e)
            logger.error(f"Failed to send {step.channel.value}: {e}")

    async def _send_push_notification(self, 
                                      escalation: EscalationEvent, 
                                      step: NotificationStep):
        """Send push notification (demo implementation)"""
        # Simulate API call delay
        await asyncio.sleep(0.1)
        logger.info(f"Push notification sent: {escalation.title}")

    async def _send_whatsapp_notification(self, 
                                          escalation: EscalationEvent, 
                                          step: NotificationStep):
        """Send WhatsApp notification (demo implementation)"""
        # Simulate API call delay
        await asyncio.sleep(0.2)
        logger.info(f"WhatsApp message sent: {escalation.message}")

    async def _send_phone_call(self, 
                               escalation: EscalationEvent, 
                               step: NotificationStep):
        """Initiate phone call (demo implementation)"""
        # Simulate API call delay
        await asyncio.sleep(0.3)
        logger.info(f"Phone call initiated for escalation: {escalation.title}")

    def get_escalation(self, escalation_id: str) -> Optional[EscalationEvent]:
        """Get escalation by ID"""
        return self.active_escalations.get(escalation_id)

    def list_escalations(self, user_id: Optional[str] = None) -> List[EscalationEvent]:
        """List all escalations, optionally filtered by user"""
        escalations = list(self.active_escalations.values())
        if user_id:
            escalations = [e for e in escalations if e.user_id == user_id]
        return escalations

    async def acknowledge_escalation(self, escalation_id: str) -> Optional[EscalationEvent]:
        """Mark an escalation as acknowledged and stop further notifications"""
        escalation = self.active_escalations.get(escalation_id)
        if not escalation:
            return None
        
        escalation.acknowledge()
        
        # Cancel the escalation task if it's still running
        task = self.escalation_tasks.get(escalation_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Escalation {escalation_id} acknowledged")
        return escalation

    async def cancel_escalation(self, escalation_id: str) -> bool:
        """Cancel an ongoing escalation"""
        escalation = self.active_escalations.get(escalation_id)
        if not escalation:
            return False
        
        escalation.is_complete = True
        
        # Cancel the task
        task = self.escalation_tasks.get(escalation_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Escalation {escalation_id} cancelled")
        return True

    def get_escalation_status(self, escalation_id: str) -> Optional[Dict]:
        """Get detailed status of an escalation"""
        escalation = self.active_escalations.get(escalation_id)
        if not escalation:
            return None
        
        return {
            "escalation": escalation.to_dict(),
            "is_running": escalation_id in self.escalation_tasks and 
                         not self.escalation_tasks[escalation_id].done()
        }


# Global service instance
_service_instance = None

def get_service() -> EscalationDemoService:
    """Get or create the global service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = EscalationDemoService()
    return _service_instance