"""Goal API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_goal_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.goal import (
    GoalCreateDTO,
    GoalDTO,
    GoalUpdateDTO,
)
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.services.dao_goal_service import DaoGoalService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=PaginatedResponse[GoalDTO])
async def list_goals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoGoalService = Depends(get_goal_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_goals(db, skip=skip, limit=limit)
    total = await service.count_goals(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/{goal_id}", response_model=GoalDTO)
async def get_goal(
    goal_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoGoalService = Depends(get_goal_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_goal(db, goal_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    return result


@router.post("/", response_model=GoalDTO, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoGoalService = Depends(get_goal_service),
    _: str = Depends(verify_service_key),
):
    return await service.create_goal(db, data)


@router.patch("/{goal_id}", response_model=GoalDTO)
async def update_goal(
    goal_id: UUID,
    data: GoalUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoGoalService = Depends(get_goal_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_goal(db, goal_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    return result


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoGoalService = Depends(get_goal_service),
    _: str = Depends(verify_service_key),
):
    deleted = await service.delete_goal(db, goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
