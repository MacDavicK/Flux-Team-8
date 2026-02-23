"""FastAPI routes for Push Notification Integration."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from .models import (
    SendPushNotificationRequest,
    PushNotificationResponse,
    SubscribeRequest,
    UnsubscribeRequest,
    VapidPublicKeyResponse,
    SubscriptionRecord,
)
from .service import PushNotificationService

router = APIRouter(prefix="/notifications/push", tags=["push-notifications"])

# Dependency injection for service
push_service = PushNotificationService()

def get_push_service() -> PushNotificationService:
    return push_service

@router.post("", response_model=PushNotificationResponse)
async def send_push_notification(
    request: SendPushNotificationRequest,
    service: PushNotificationService = Depends(get_push_service)
) -> PushNotificationResponse:
    """Send push notification to user's devices."""
    try:
        return await service.send_push_notification(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/subscribe")
async def subscribe(
    request: SubscribeRequest,
    service: PushNotificationService = Depends(get_push_service)
):
    """Register push notification subscription."""
    subscription_record = SubscriptionRecord(
        user_id=request.user_id,
        device_id=request.device_id,
        device_name=request.device_name,
        subscription=request.subscription,
        user_agent=request.user_agent,
    )
    success = await service.subscribe(subscription_record)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register subscription")
    return {"success": True, "message": "Subscription registered successfully"}

@router.delete("/unsubscribe")
async def unsubscribe(
    request: UnsubscribeRequest,
    service: PushNotificationService = Depends(get_push_service)
):
    """Remove push notification subscription."""
    success = await service.unsubscribe(request.user_id, request.device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"success": True, "message": "Subscription removed successfully"}

@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key(
    service: PushNotificationService = Depends(get_push_service)
) -> VapidPublicKeyResponse:
    """Get VAPID public key for client subscription."""
    return VapidPublicKeyResponse(public_key=service.get_vapid_public_key())
