"""
Unit tests for WhatsApp API routes
"""

import pytest
from unittest.mock import Mock, patch
import json
from flask import Flask

from ..routes import whatsapp_bp
from ..service import WhatsAppServiceError
from ..models import WhatsAppNotification, NotificationStatus


@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.register_blueprint(whatsapp_bp)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestWhatsAppRoutes:
    """Test suite for WhatsApp API routes"""
    
    def test_send_message_success(self, client):
        """Test successful message sending"""
        # Mock notification response
        mock_notification = WhatsAppNotification(
            task_id='task-123',
            task_title='Complete project',
            recipient_number='whatsapp:+15551234567',
            message='Test message',
            status=NotificationStatus.SENT,
            message_sid='SM1234567890',
            app_link='https://test-app.com/tasks/task-123'
        )
        
        with patch('backend.scrum_42_whatsapp_message_integration.routes.get_whatsapp_service') as mock_service:
            mock_service.return_value.send_message.return_value = mock_notification
            
            response = client.post(
                '/notifications/whatsapp',
                data=json.dumps({
                    'task_id': 'task-123',
                    'task_title': 'Complete project',
                    'recipient_number': '+15551234567'
                }),
                content_type='application/json'
            )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'message' in data
        assert data['data']['task_id'] == 'task-123'
        assert data['data']['status'] == 'sent'
    
    def test_send_message_missing_fields(self, client):
        """Test validation of required fields"""
        response = client.post(
            '/notifications/whatsapp',
            data=json.dumps({
                'task_id': 'task-123'
                # Missing task_title and recipient_number
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing required field' in data['error']
    
    def test_send_message_invalid_json(self, client):
        """Test handling of invalid JSON"""
        response = client.post(
            '/notifications/whatsapp',
            data='invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_send_message_service_error(self, client):
        """Test handling of service errors"""
        with patch('backend.scrum_42_whatsapp_message_integration.routes.get_whatsapp_service') as mock_service:
            mock_service.return_value.send_message.side_effect = WhatsAppServiceError("Twilio error")
            
            response = client.post(
                '/notifications/whatsapp',
                data=json.dumps({
                    'task_id': 'task-123',
                    'task_title': 'Test',
                    'recipient_number': '+15551234567'
                }),
                content_type='application/json'
            )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to send WhatsApp message' in data['error']
    
    def test_send_message_with_custom_message(self, client):
        """Test sending with custom message"""
        mock_notification = WhatsAppNotification(
            task_id='task-123',
            task_title='Test',
            recipient_number='whatsapp:+15551234567',
            message='Custom message',
            status=NotificationStatus.SENT,
            message_sid='SM1234567890',
            app_link='https://test-app.com/tasks/task-123'
        )
        
        with patch('backend.scrum_42_whatsapp_message_integration.routes.get_whatsapp_service') as mock_service:
            mock_service.return_value.send_message.return_value = mock_notification
            
            response = client.post(
                '/notifications/whatsapp',
                data=json.dumps({
                    'task_id': 'task-123',
                    'task_title': 'Test',
                    'recipient_number': '+15551234567',
                    'custom_message': 'Custom message'
                }),
                content_type='application/json'
            )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
    
    def test_get_message_status_success(self, client):
        """Test retrieving message status"""
        mock_status = {
            'sid': 'SM1234567890',
            'status': 'delivered',
            'date_sent': '2026-02-15T21:00:00Z',
            'date_updated': '2026-02-15T21:00:05Z',
            'error_code': None,
            'error_message': None
        }
        
        with patch('backend.scrum_42_whatsapp_message_integration.routes.get_whatsapp_service') as mock_service:
            mock_service.return_value.get_message_status.return_value = mock_status
            
            response = client.get('/notifications/whatsapp/status/SM1234567890')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['sid'] == 'SM1234567890'
        assert data['data']['status'] == 'delivered'
    
    def test_get_message_status_error(self, client):
        """Test error handling when fetching message status"""
        with patch('backend.scrum_42_whatsapp_message_integration.routes.get_whatsapp_service') as mock_service:
            mock_service.return_value.get_message_status.side_effect = WhatsAppServiceError("Message not found")
            
            response = client.get('/notifications/whatsapp/status/SM1234567890')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to fetch message status' in data['error']
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/notifications/whatsapp/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'whatsapp'
