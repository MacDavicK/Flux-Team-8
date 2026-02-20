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
    Send a WhatsApp Message
    ---
    tags:
      - whatsapp
    summary: Send WhatsApp Message
    description: Send a WhatsApp notification via Twilio to the specified phone number.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - task_id
            - task_title
            - recipient_number
          properties:
            task_id:
              type: string
              example: task-abc-123
            task_title:
              type: string
              example: Complete project report
            recipient_number:
              type: string
              description: Phone in E.164 format
              example: "+15551234567"
            custom_message:
              type: string
              example: Please complete your task.
    responses:
      200:
        description: Message sent successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message_sid:
              type: string
              example: SM1234567890abcdef
            status:
              type: string
              example: queued
      400:
        description: Missing required fields
      500:
        description: Twilio API error
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
    Get WhatsApp Message Status
    ---
    tags:
      - whatsapp
    summary: Get Message Delivery Status
    description: Retrieve the delivery status of a WhatsApp message by its Twilio MessageSid.
    parameters:
      - in: path
        name: message_sid
        required: true
        type: string
        description: Twilio MessageSid
        example: SM1234567890abcdef
    responses:
      200:
        description: Message status retrieved
        schema:
          type: object
          properties:
            message_sid:
              type: string
            status:
              type: string
              example: delivered
            date_sent:
              type: string
      404:
        description: Message not found
      500:
        description: Twilio API error
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
    Health Check
    ---
    tags:
      - health
    summary: Service Health Check
    description: Returns health status of the WhatsApp Message Integration service.
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            service:
              type: string
              example: whatsapp_message_integration
            version:
              type: string
              example: 1.0.0
    """
    return jsonify({
        'status': 'healthy',
        'service': 'whatsapp'
    }), 200
