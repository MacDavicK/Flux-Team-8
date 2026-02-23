"""
Unit tests for WhatsAppService
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ..service import WhatsAppService, WhatsAppServiceError
from ..models import NotificationStatus


class TestWhatsAppService:
    """Test suite for WhatsAppService"""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables"""
        monkeypatch.setenv('TWILIO_ACCOUNT_SID', 'test_account_sid')
        monkeypatch.setenv('TWILIO_AUTH_TOKEN', 'test_auth_token')
        monkeypatch.setenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
        monkeypatch.setenv('APP_BASE_URL', 'https://test-app.com')
    
    @pytest.fixture
    def service(self, mock_env):
        """Create WhatsAppService instance"""
        with patch('twilio.rest.Client'):
            return WhatsAppService()
    
    def test_initialization_success(self, mock_env):
        """Test successful service initialization"""
        with patch('twilio.rest.Client') as mock_client:
            service = WhatsAppService()
            assert service.account_sid == 'test_account_sid'
            assert service.auth_token == 'test_auth_token'
            assert service.whatsapp_from == 'whatsapp:+14155238886'
            mock_client.assert_called_once_with('test_account_sid', 'test_auth_token')
    
    def test_initialization_missing_credentials(self, monkeypatch):
        """Test initialization fails without credentials"""
        monkeypatch.delenv('TWILIO_ACCOUNT_SID', raising=False)
        monkeypatch.delenv('TWILIO_AUTH_TOKEN', raising=False)
        
        with pytest.raises(WhatsAppServiceError, match="must be set in environment variables"):
            WhatsAppService()
    
    def test_format_message(self, service):
        """Test message formatting"""
        task_title = "Complete project"
        task_id = "task-123"
        
        message, app_link = service.format_message(task_title, task_id)
        
        assert "Hey! Don't forget: Complete project" in message
        assert "🎯" in message
        assert "https://test-app.com/tasks/task-123" in message
        assert app_link == "https://test-app.com/tasks/task-123"
    
    def test_send_message_success(self, service):
        """Test successful message sending"""
        # Mock Twilio message response
        mock_message = Mock()
        mock_message.sid = 'SM1234567890'
        service.client.messages.create = Mock(return_value=mock_message)
        
        # Send message
        notification = service.send_message(
            task_id='task-123',
            task_title='Complete project',
            recipient_number='+15551234567'
        )
        
        # Verify results
        assert notification.status == NotificationStatus.SENT
        assert notification.message_sid == 'SM1234567890'
        assert notification.task_id == 'task-123'
        assert notification.sent_at is not None
        assert 'whatsapp:' in notification.recipient_number
        
        # Verify Twilio API was called correctly
        service.client.messages.create.assert_called_once()
        call_kwargs = service.client.messages.create.call_args[1]
        assert call_kwargs['to'] == 'whatsapp:+15551234567'
        assert call_kwargs['from_'] == 'whatsapp:+14155238886'
    
    def test_send_message_adds_whatsapp_prefix(self, service):
        """Test that whatsapp: prefix is added to recipient number"""
        mock_message = Mock()
        mock_message.sid = 'SM1234567890'
        service.client.messages.create = Mock(return_value=mock_message)
        
        notification = service.send_message(
            task_id='task-123',
            task_title='Test',
            recipient_number='+15551234567'
        )
        
        assert notification.recipient_number == 'whatsapp:+15551234567'
    
    def test_send_message_custom_message(self, service):
        """Test sending with custom message"""
        mock_message = Mock()
        mock_message.sid = 'SM1234567890'
        service.client.messages.create = Mock(return_value=mock_message)
        
        custom_msg = "Custom reminder message"
        notification = service.send_message(
            task_id='task-123',
            task_title='Test',
            recipient_number='+15551234567',
            custom_message=custom_msg
        )
        
        assert notification.message == custom_msg
        call_kwargs = service.client.messages.create.call_args[1]
        assert call_kwargs['body'] == custom_msg
    
    def test_send_message_twilio_error(self, service):
        """Test handling of Twilio API errors"""
        from twilio.base.exceptions import TwilioRestException
        
        # Mock Twilio error
        error = TwilioRestException(
            status=400,
            uri='/Messages',
            msg='Invalid phone number',
            code=21211
        )
        service.client.messages.create = Mock(side_effect=error)
        
        # Verify error is raised and logged
        with pytest.raises(WhatsAppServiceError, match="Twilio error"):
            service.send_message(
                task_id='task-123',
                task_title='Test',
                recipient_number='invalid'
            )
    
    def test_send_message_unexpected_error(self, service):
        """Test handling of unexpected errors"""
        service.client.messages.create = Mock(side_effect=Exception("Network error"))
        
        with pytest.raises(WhatsAppServiceError, match="Unexpected error"):
            service.send_message(
                task_id='task-123',
                task_title='Test',
                recipient_number='+15551234567'
            )
    
    def test_get_message_status_success(self, service):
        """Test retrieving message status"""
        # Mock Twilio message status response
        mock_message = Mock()
        mock_message.sid = 'SM1234567890'
        mock_message.status = 'delivered'
        mock_message.date_sent = datetime(2026, 2, 15, 21, 0, 0)
        mock_message.date_updated = datetime(2026, 2, 15, 21, 0, 5)
        mock_message.error_code = None
        mock_message.error_message = None
        
        service.client.messages = Mock(return_value=Mock(fetch=Mock(return_value=mock_message)))
        
        status_info = service.get_message_status('SM1234567890')
        
        assert status_info['sid'] == 'SM1234567890'
        assert status_info['status'] == 'delivered'
        assert status_info['error_code'] is None
    
    def test_get_message_status_error(self, service):
        """Test error handling when fetching message status"""
        from twilio.base.exceptions import TwilioRestException
        
        error = TwilioRestException(
            status=404,
            uri='/Messages/SM1234567890',
            msg='Message not found',
            code=20404
        )
        service.client.messages = Mock(return_value=Mock(fetch=Mock(side_effect=error)))
        
        with pytest.raises(WhatsAppServiceError, match="Failed to fetch message status"):
            service.get_message_status('SM1234567890')
