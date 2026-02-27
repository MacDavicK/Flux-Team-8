"""
Tests for NotificationPriorityService
"""
import pytest
from backend.scrum_40_notification_priority_model.service import NotificationPriorityService
from backend.scrum_40_notification_priority_model.models import (
    NotificationPriority,
    NotificationRequest,
    EscalationChannel
)


class TestNotificationPriorityService:
    """Test cases for NotificationPriorityService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = NotificationPriorityService()
    
    def test_standard_priority_escalation_path(self):
        """Test that standard priority has push only"""
        path = self.service.get_escalation_path(NotificationPriority.STANDARD)
        assert len(path.steps) == 1
        assert path.steps[0].channel == EscalationChannel.PUSH
        assert path.steps[0].wait_time_seconds == 0
    
    def test_important_priority_escalation_path(self):
        """Test that important priority has push and WhatsApp"""
        path = self.service.get_escalation_path(NotificationPriority.IMPORTANT)
        assert len(path.steps) == 2
        assert path.steps[0].channel == EscalationChannel.PUSH
        assert path.steps[1].channel == EscalationChannel.WHATSAPP
        assert path.steps[1].wait_time_seconds == 120  # 2 minutes
    
    def test_must_not_miss_priority_escalation_path(self):
        """Test that must-not-miss priority has push, WhatsApp, and call"""
        path = self.service.get_escalation_path(NotificationPriority.MUST_NOT_MISS)
        assert len(path.steps) == 3
        assert path.steps[0].channel == EscalationChannel.PUSH
        assert path.steps[1].channel == EscalationChannel.WHATSAPP
        assert path.steps[2].channel == EscalationChannel.CALL
        assert path.steps[1].wait_time_seconds == 120  # 2 minutes
        assert path.steps[2].wait_time_seconds == 420  # 7 minutes
    
    def test_speed_multiplier_1x(self):
        """Test that 1x multiplier doesn't change wait times"""
        path = self.service.get_escalation_path(NotificationPriority.IMPORTANT)
        actual_times = self.service.apply_speed_multiplier(path, 1.0)
        assert actual_times == [0, 120]
    
    def test_speed_multiplier_10x(self):
        """Test that 10x multiplier reduces wait times by factor of 10"""
        path = self.service.get_escalation_path(NotificationPriority.MUST_NOT_MISS)
        actual_times = self.service.apply_speed_multiplier(path, 10.0)
        # 120s / 10 = 12s, 420s / 10 = 42s
        assert actual_times == [0, 12, 42]
    
    def test_speed_multiplier_5x(self):
        """Test that 5x multiplier reduces wait times by factor of 5"""
        path = self.service.get_escalation_path(NotificationPriority.IMPORTANT)
        actual_times = self.service.apply_speed_multiplier(path, 5.0)
        # 120s / 5 = 24s
        assert actual_times == [0, 24]
    
    def test_send_notification_standard(self):
        """Test sending a standard priority notification"""
        request = NotificationRequest(
            user_id="user123",
            priority=NotificationPriority.STANDARD,
            escalation_speed_multiplier=1.0,
            message="Test notification"
        )
        response = self.service.send_notification(request)
        
        assert response.user_id == "user123"
        assert response.priority == NotificationPriority.STANDARD
        assert response.status == "sent"
        assert len(response.actual_wait_times) == 1
        assert response.actual_wait_times[0] == 0
    
    def test_send_notification_must_not_miss_10x(self):
        """Test sending a must-not-miss notification with 10x multiplier"""
        request = NotificationRequest(
            user_id="user456",
            priority=NotificationPriority.MUST_NOT_MISS,
            escalation_speed_multiplier=10.0,
            message="Urgent notification"
        )
        response = self.service.send_notification(request)
        
        assert response.user_id == "user456"
        assert response.priority == NotificationPriority.MUST_NOT_MISS
        assert response.status == "sent"
        assert response.actual_wait_times == [0, 12, 42]
    
    def test_calculate_escalation_timing(self):
        """Test escalation timing calculation"""
        timing = self.service.calculate_escalation_timing(
            NotificationPriority.MUST_NOT_MISS,
            10.0
        )
        
        assert timing["priority"] == NotificationPriority.MUST_NOT_MISS
        assert timing["multiplier"] == 10.0
        assert len(timing["steps"]) == 3
        
        # Check first step
        assert timing["steps"][0]["channel"] == EscalationChannel.PUSH
        assert timing["steps"][0]["actual_wait_time_seconds"] == 0
        
        # Check second step
        assert timing["steps"][1]["channel"] == EscalationChannel.WHATSAPP
        assert timing["steps"][1]["actual_wait_time_seconds"] == 12
        assert timing["steps"][1]["cumulative_time_seconds"] == 12
        
        # Check third step
        assert timing["steps"][2]["channel"] == EscalationChannel.CALL
        assert timing["steps"][2]["actual_wait_time_seconds"] == 42
        assert timing["steps"][2]["cumulative_time_seconds"] == 54
