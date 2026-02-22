"""Task API endpoints including Scheduler and Observer specialized endpoints."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_task_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.schemas.task import (
    BulkUpdateResponse,
    BulkUpdateStateRequest,
    TaskCreateDTO,
    TaskDTO,
    TaskStatisticsDTO,
    TaskUpdateDTO,
)
from dao_service.services.dao_task_service import DaoTaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=PaginatedResponse[TaskDTO])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_tasks(db, skip=skip, limit=limit)
    total = await service.count_tasks(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/by-timerange", response_model=List[TaskDTO])
async def get_tasks_by_timerange(
    user_id: UUID,
    start_at: datetime,
    end_at: datetime,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    return await service.get_tasks_for_scheduling(db, user_id, start_at, end_at)


@router.get("/statistics", response_model=TaskStatisticsDTO)
async def get_task_statistics(
    user_id: UUID,
    start_date: datetime,
    end_date: datetime,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    return await service.get_task_statistics(db, user_id, start_date, end_date)


@router.get("/{task_id}", response_model=TaskDTO)
async def get_task(
    task_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_task(db, task_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return result


@router.post("/", response_model=TaskDTO, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    return await service.create_task(db, data)


@router.patch("/{task_id}", response_model=TaskDTO)
async def update_task(
    task_id: UUID,
    data: TaskUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_task(db, task_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return result


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    deleted = await service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.post("/bulk-update-state", response_model=BulkUpdateResponse)
async def bulk_update_task_state(
    data: BulkUpdateStateRequest,
    db: DatabaseSession = Depends(get_db),
    service: DaoTaskService = Depends(get_task_service),
    _: str = Depends(verify_service_key),
):
    count = await service.bulk_update_status(db, data.task_ids, data.new_status)
    return BulkUpdateResponse(updated_count=count)
