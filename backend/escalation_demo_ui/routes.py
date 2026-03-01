"""REST API routes for escalation demo"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any
import logging

from .service import get_service
from .models import EscalationSpeed

logger = logging.getLogger(__name__)

# Create Blueprint
escalation_demo_bp = Blueprint('escalation_demo', __name__, url_prefix='/api/escalation-demo')


@escalation_demo_bp.route('/health', methods=['GET'])
def health_check() -> tuple[Dict[str, Any], int]:
    """
    Health Check
    ---
    tags:
      - health
    summary: Service Health Check
    description: Returns health status of the Escalation Demo UI service.
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
              example: escalation_demo_ui
            version:
              type: string
              example: 1.0.0
    """
    return jsonify({
        "status": "healthy",
        "service": "escalation-demo"
    }), 200


@escalation_demo_bp.route('/trigger', methods=['POST'])
async def trigger_escalation() -> tuple[Dict[str, Any], int]:
    """
    Trigger Escalation
    ---
    tags:
      - escalation
    summary: Trigger Escalation Sequence
    description: Start a multi-channel escalation (push notification, WhatsApp, phone call) for a task.
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
            - priority
          properties:
            task_id:
              type: string
              example: task-xyz-789
            task_title:
              type: string
              example: Submit quarterly report
            priority:
              type: string
              enum: [standard, important, must_not_miss]
              example: important
            recipient_phone:
              type: string
              example: "+15551234567"
    responses:
      201:
        description: Escalation triggered
      400:
        description: Missing required fields
      500:
        description: Service error
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        user_id = data.get('user_id')
        title = data.get('title')
        message = data.get('message')
        speed_str = data.get('speed', '1x')
        
        if not all([user_id, title, message]):
            return jsonify({
                "error": "Missing required fields",
                "required": ["user_id", "title", "message"]
            }), 400
        
        # Parse speed
        try:
            speed = EscalationSpeed(speed_str)
        except ValueError:
            return jsonify({
                "error": f"Invalid speed value: {speed_str}",
                "valid_values": ["1x", "5x", "10x"]
            }), 400
        
        # Create escalation
        service = get_service()
        escalation = await service.create_escalation(
            user_id=user_id,
            title=title,
            message=message,
            speed=speed
        )
        
        logger.info(f"Triggered escalation {escalation.id} for user {user_id}")
        
        return jsonify({
            "success": True,
            "escalation": escalation.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error triggering escalation: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@escalation_demo_bp.route('/escalations/<escalation_id>', methods=['GET'])
def get_escalation(escalation_id: str) -> tuple[Dict[str, Any], int]:
    """
    Get Escalation
    ---
    tags:
      - escalation
    summary: Get Escalation Details
    description: Retrieve details and status of a specific escalation sequence.
    parameters:
      - in: path
        name: escalation_id
        required: true
        type: string
        example: esc-abc-123
    responses:
      200:
        description: Escalation details
      404:
        description: Escalation not found
    """
    try:
        service = get_service()
        status = service.get_escalation_status(escalation_id)
        
        if not status:
            return jsonify({
                "error": "Escalation not found",
                "escalation_id": escalation_id
            }), 404
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting escalation {escalation_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@escalation_demo_bp.route('/escalations', methods=['GET'])
def list_escalations() -> tuple[Dict[str, Any], int]:
    """
    List Escalations
    ---
    tags:
      - escalation
    summary: List All Escalations
    description: Retrieve all escalation sequences, optionally filtered by status.
    parameters:
      - in: query
        name: status
        required: false
        type: string
        example: in_progress
    responses:
      200:
        description: List of escalations
    """
    try:
        user_id = request.args.get('user_id')
        
        service = get_service()
        escalations = service.list_escalations(user_id=user_id)
        
        return jsonify({
            "escalations": [e.to_dict() for e in escalations],
            "count": len(escalations)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing escalations: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@escalation_demo_bp.route('/escalations/<escalation_id>/acknowledge', methods=['POST'])
async def acknowledge_escalation(escalation_id: str) -> tuple[Dict[str, Any], int]:
    """
    Acknowledge Escalation
    ---
    tags:
      - escalation
    summary: Acknowledge Escalation
    description: Mark an escalation as acknowledged, stopping further escalation steps.
    parameters:
      - in: path
        name: escalation_id
        required: true
        type: string
        example: esc-abc-123
    responses:
      200:
        description: Escalation acknowledged
      404:
        description: Escalation not found
      409:
        description: Already acknowledged or cancelled
    """
    try:
        service = get_service()
        escalation = await service.acknowledge_escalation(escalation_id)
        
        if not escalation:
            return jsonify({
                "error": "Escalation not found",
                "escalation_id": escalation_id
            }), 404
        
        logger.info(f"Escalation {escalation_id} acknowledged")
        
        return jsonify({
            "success": True,
            "escalation": escalation.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error acknowledging escalation {escalation_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@escalation_demo_bp.route('/escalations/<escalation_id>/cancel', methods=['POST'])
async def cancel_escalation(escalation_id: str) -> tuple[Dict[str, Any], int]:
    """
    Cancel Escalation
    ---
    tags:
      - escalation
    summary: Cancel Escalation
    description: Cancel an active escalation sequence before it completes.
    parameters:
      - in: path
        name: escalation_id
        required: true
        type: string
        example: esc-abc-123
    responses:
      200:
        description: Escalation cancelled
      404:
        description: Escalation not found
      409:
        description: Already completed or cancelled
    """
    try:
        service = get_service()
        success = await service.cancel_escalation(escalation_id)
        
        if not success:
            return jsonify({
                "error": "Escalation not found",
                "escalation_id": escalation_id
            }), 404
        
        logger.info(f"Escalation {escalation_id} cancelled")
        
        return jsonify({
            "success": True,
            "message": "Escalation cancelled successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error cancelling escalation {escalation_id}: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500