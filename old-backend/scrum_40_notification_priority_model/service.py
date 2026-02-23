"""
Business logic for Notification Priority Model
"""
import uuid
from datetime import datetime
from typing import Dict
from .models import (
    NotificationPriority,
    EscalationChannel,
    EscalationStep,
    EscalationPath,
    NotificationRequest,
    NotificationResponse,
    EscalationConfig
)


class NotificationPriorityService:
    """
    Service for managing notification priorities and escalation paths
    """
    
    def __init__(self):
        """Initialize with default escalation configuration"""
        self.escalation_config = self._create_default_config()
    
    def _create_default_config(self) -> EscalationConfig:
        """
        Create the default escalation configuration based on SCRUM-40 requirements:
        - Standard: push only
        - Important: push → WhatsApp (after 2 min if no ack)
        - Must-Not-Miss: push → WhatsApp (2 min) → Call (7 min)
        """
        standard_path = EscalationPath(
            priority=NotificationPriority.STANDARD,
            steps=[
                EscalationStep(channel=EscalationChannel.PUSH, wait_time_seconds=0)
            ]
        )
        
        important_path = EscalationPath(
            priority=NotificationPriority.IMPORTANT,
            steps=[
                EscalationStep(channel=EscalationChannel.PUSH, wait_time_seconds=0),
                EscalationStep(channel=EscalationChannel.WHATSAPP, wait_time_seconds=120)  # 2 min
            ]
        )
        
        must_not_miss_path = EscalationPath(
            priority=NotificationPriority.MUST_NOT_MISS,
            steps=[
                EscalationStep(channel=EscalationChannel.PUSH, wait_time_seconds=0),
                EscalationStep(channel=EscalationChannel.WHATSAPP, wait_time_seconds=120),  # 2 min
                EscalationStep(channel=EscalationChannel.CALL, wait_time_seconds=420)  # 7 min total
            ]
        )
        
        return EscalationConfig(
            standard=standard_path,
            important=important_path,
            must_not_miss=must_not_miss_path
        )
    
    def get_escalation_path(self, priority: NotificationPriority) -> EscalationPath:
        """
        Get the escalation path for a given priority level
        """
        priority_map = {
            NotificationPriority.STANDARD: self.escalation_config.standard,
            NotificationPriority.IMPORTANT: self.escalation_config.important,
            NotificationPriority.MUST_NOT_MISS: self.escalation_config.must_not_miss
        }
        return priority_map[priority]
    
    def apply_speed_multiplier(
        self,
        escalation_path: EscalationPath,
        multiplier: float
    ) -> list[int]:
        """
        Apply escalation speed multiplier to reduce wait times.
        Multiplier of 1x = normal, 5x = 5 times faster, 10x = 10 times faster.
        
        Example: With 10x multiplier, 2 min (120s) becomes 12s instead of 2 min.
        """
        actual_wait_times = []
        for step in escalation_path.steps:
            # Divide wait time by multiplier to make it faster
            adjusted_time = int(step.wait_time_seconds / multiplier)
            actual_wait_times.append(adjusted_time)
        return actual_wait_times
    
    def send_notification(self, request: NotificationRequest) -> NotificationResponse:
        """
        Send a notification with the specified priority and escalation speed.
        Returns details about the notification including escalation path and actual wait times.
        """
        # Generate unique notification ID
        notification_id = str(uuid.uuid4())
        
        # Get escalation path based on priority
        escalation_path = self.get_escalation_path(request.priority)
        
        # Apply escalation speed multiplier
        actual_wait_times = self.apply_speed_multiplier(
            escalation_path,
            request.escalation_speed_multiplier
        )
        
        # TODO: Integrate with actual notification channels (push, WhatsApp, call)
        # For now, we return the response with the calculated escalation details
        
        response = NotificationResponse(
            notification_id=notification_id,
            user_id=request.user_id,
            priority=request.priority,
            escalation_path=escalation_path,
            actual_wait_times=actual_wait_times,
            created_at=datetime.utcnow(),
            status="sent"
        )
        
        return response
    
    def get_all_escalation_paths(self) -> EscalationConfig:
        """
        Get all configured escalation paths
        """
        return self.escalation_config
    
    def calculate_escalation_timing(
        self,
        priority: NotificationPriority,
        multiplier: float = 1.0
    ) -> Dict[str, any]:
        """
        Calculate and return detailed escalation timing for a priority level.
        Useful for debugging and understanding escalation behavior.
        """
        escalation_path = self.get_escalation_path(priority)
        actual_wait_times = self.apply_speed_multiplier(escalation_path, multiplier)
        
        timing_details = {
            "priority": priority,
            "multiplier": multiplier,
            "steps": []
        }
        
        cumulative_time = 0
        for i, (step, actual_wait) in enumerate(zip(escalation_path.steps, actual_wait_times)):
            cumulative_time += actual_wait
            timing_details["steps"].append({
                "step_number": i + 1,
                "channel": step.channel,
                "base_wait_time_seconds": step.wait_time_seconds,
                "actual_wait_time_seconds": actual_wait,
                "cumulative_time_seconds": cumulative_time,
                "time_from_start_human_readable": self._format_time(cumulative_time)
            })
        
        return timing_details
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds into human-readable time"""
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds}s"
