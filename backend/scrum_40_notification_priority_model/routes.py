"""
FastAPI routes for Notification Priority Model API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from .models import (
    NotificationRequest,
    NotificationResponse,
    NotificationPriority,
    EscalationConfig
)
from .service import NotificationPriorityService

priority_router = APIRouter(
    prefix="/api/v1/notifications/priority",
    tags=["Notification Priority"]
)

# Initialize service
service = NotificationPriorityService()


@priority_router.post("/send", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest):
    """
    Send a notification with specified priority and escalation settings.
    
    - **user_id**: ID of the user to notify
    - **priority**: Priority level (standard/important/must_not_miss)
    - **escalation_speed_multiplier**: Speed multiplier (1x, 5x, or 10x)
    - **message**: Notification message content
    - **metadata**: Optional additional metadata
    
    Returns notification details including escalation path and actual wait times.
    """
    try:
        response = service.send_notification(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@priority_router.get("/config", response_model=EscalationConfig)
async def get_escalation_config():
    """
    Get the complete escalation configuration for all priority levels.
    
    Returns escalation paths for standard, important, and must-not-miss priorities.
    """
    return service.get_all_escalation_paths()


@priority_router.get("/timing")
async def calculate_timing(
    priority: NotificationPriority = Query(..., description="Priority level"),
    multiplier: float = Query(1.0, ge=1.0, le=10.0, description="Escalation speed multiplier")
):
    """
    Calculate detailed escalation timing for a specific priority and multiplier.
    
    Useful for understanding how escalation will behave with different settings.
    
    - **priority**: Priority level to calculate timing for
    - **multiplier**: Speed multiplier (1x, 5x, or 10x)
    
    Returns step-by-step timing details with cumulative times.
    """
    try:
        timing_details = service.calculate_escalation_timing(priority, multiplier)
        return timing_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@priority_router.get("/health")
async def health_check():
    """
    Health check endpoint for the notification priority service.
    """
    return {
        "status": "healthy",
        "service": "notification_priority_model",
        "version": "1.0.0"
    }
