"""
REST API routes for WhatsApp notification service
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from .service import WhatsAppService, WhatsAppServiceError
from .models import NotificationStatus


logger = logging.getLogger(__name__)

# Create Blueprint
whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/notifications/whatsapp')

# Initialize service (will be initialized per request to handle errors gracefully)


def get_whatsapp_service() -> WhatsAppService:
    """Factory function to create WhatsAppService instance"""
    try:
        return WhatsAppService()
    except WhatsAppServiceError as e:
        logger.error(f"Failed to initialize WhatsAppService: {e}")
        raise


@whatsapp_bp.route('/', methods=['POST'])
def send_whatsapp_message() -> tuple[Dict[str, Any], int]:
    """
    Send a WhatsApp notification message
    
    POST /notifications/whatsapp
    
    Request Body:
    {
        "task_id": "string",
        "task_title": "string",
        "recipient_number": "string (E.164 format, e.g., +15551234567)",
        "custom_message": "string (optional)"
    }
    
    Response (200 OK):
    {
        "success": true,
        "message": "WhatsApp message sent successfully",
        "data": {
            "task_id": "string",
            "task_title": "string",
            "recipient_number": "string",
            "message": "string",
            "status": "sent",
            "message_sid": "string",
            "sent_at": "ISO 8601 timestamp",
            "app_link": "string"
        }
    }
    
    Response (400 Bad Request):
    {
        "success": false,
        "error": "Missing required field: task_id"
    }
    
    Response (500 Internal Server Error):
    {
        "success": false,
        "error": "Failed to send WhatsApp message",
        "details": "Error details"
    }
    """
    try:
        # Parse request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be JSON'
            }), 400
        
        # Validate required fields
        required_fields = ['task_id', 'task_title', 'recipient_number']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        task_id = data['task_id']
        task_title = data['task_title']
        recipient_number = data['recipient_number']
        custom_message = data.get('custom_message')
        
        # Initialize service and send message
        service = get_whatsapp_service()
        notification = service.send_message(
            task_id=task_id,
            task_title=task_title,
            recipient_number=recipient_number,
            custom_message=custom_message
        )
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'WhatsApp message sent successfully',
            'data': notification.to_dict()
        }), 200
        
    except WhatsAppServiceError as e:
        # Handle WhatsApp service errors (Twilio errors, etc.)
        logger.error(f"WhatsApp service error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to send WhatsApp message',
            'details': str(e)
        }), 500
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in send_whatsapp_message: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500


@whatsapp_bp.route('/status/<message_sid>', methods=['GET'])
def get_message_status(message_sid: str) -> tuple[Dict[str, Any], int]:
    """
    Get the status of a sent WhatsApp message
    
    GET /notifications/whatsapp/status/<message_sid>
    
    Response (200 OK):
    {
        "success": true,
        "data": {
            "sid": "string",
            "status": "string",
            "date_sent": "ISO 8601 timestamp",
            "date_updated": "ISO 8601 timestamp",
            "error_code": "string or null",
            "error_message": "string or null"
        }
    }
    
    Response (500 Internal Server Error):
    {
        "success": false,
        "error": "Failed to fetch message status",
        "details": "Error details"
    }
    """
    try:
        service = get_whatsapp_service()
        status_info = service.get_message_status(message_sid)
        
        return jsonify({
            'success': True,
            'data': status_info
        }), 200
        
    except WhatsAppServiceError as e:
        logger.error(f"Failed to fetch message status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch message status',
            'details': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get_message_status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500


@whatsapp_bp.route('/health', methods=['GET'])
def health_check() -> tuple[Dict[str, Any], int]:
    """
    Health check endpoint
    
    GET /notifications/whatsapp/health
    
    Response (200 OK):
    {
        "status": "healthy",
        "service": "whatsapp"
    }
    """
    return jsonify({
        'status': 'healthy',
        'service': 'whatsapp'
    }), 200
