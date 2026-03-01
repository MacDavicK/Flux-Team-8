"""Notification log API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_notification_log_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.notification_log import (
    NotificationLogCreateDTO,
    NotificationLogDTO,
    NotificationLogUpdateDTO,
)
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.services.dao_notification_log_service import DaoNotificationLogService

router = APIRouter(prefix="/notification-log", tags=["notification-log"])


@router.get("/", response_model=PaginatedResponse[NotificationLogDTO])
async def list_notification_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoNotificationLogService = Depends(get_notification_log_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_notification_logs(db, skip=skip, limit=limit)
    total = await service.count_notification_logs(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/{notification_log_id}", response_model=NotificationLogDTO)
async def get_notification_log(
    notification_log_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoNotificationLogService = Depends(get_notification_log_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_notification_log(db, notification_log_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Notification log {notification_log_id} not found"
        )
    return result


@router.post("/", response_model=NotificationLogDTO, status_code=status.HTTP_201_CREATED)
async def create_notification_log(
    data: NotificationLogCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoNotificationLogService = Depends(get_notification_log_service),
    _: str = Depends(verify_service_key),
):
    return await service.create_notification_log(db, data)


@router.patch("/{notification_log_id}", response_model=NotificationLogDTO)
async def update_notification_log(
    notification_log_id: UUID,
    data: NotificationLogUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoNotificationLogService = Depends(get_notification_log_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_notification_log(db, notification_log_id, data)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Notification log {notification_log_id} not found"
        )
    return result


@router.delete("/{notification_log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_log(
    notification_log_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoNotificationLogService = Depends(get_notification_log_service),
    _: str = Depends(verify_service_key),
):
    deleted = await service.delete_notification_log(db, notification_log_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Notification log {notification_log_id} not found"
        )
