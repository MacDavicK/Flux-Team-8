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
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "escalation-demo"
    }), 200


@escalation_demo_bp.route('/trigger', methods=['POST'])
async def trigger_escalation() -> tuple[Dict[str, Any], int]:
    """Trigger a new escalation flow
    
    Request body:
    {
        "user_id": "string",
        "title": "string",
        "message": "string",
        "speed": "1x" | "5x" | "10x"  (optional, default: "1x")
    }
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
    """Get details of a specific escalation"""
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
    """List all escalations
    
    Query parameters:
    - user_id: Filter by user ID (optional)
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
    """Acknowledge an escalation and stop further notifications"""
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
    """Cancel an ongoing escalation"""
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