"""Milestone API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_milestone_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.core.exceptions import ForeignKeyError
from dao_service.schemas.milestone import MilestoneCreateDTO, MilestoneDTO, MilestoneUpdateDTO
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.services.dao_milestone_service import DaoMilestoneService

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("/", response_model=PaginatedResponse[MilestoneDTO])
async def list_milestones(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoMilestoneService = Depends(get_milestone_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_milestones(db, skip=skip, limit=limit)
    total = await service.count_milestones(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/{milestone_id}", response_model=MilestoneDTO)
async def get_milestone(
    milestone_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoMilestoneService = Depends(get_milestone_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_milestone(db, milestone_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Milestone {milestone_id} not found")
    return result


@router.post("/", response_model=MilestoneDTO, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    data: MilestoneCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoMilestoneService = Depends(get_milestone_service),
    _: str = Depends(verify_service_key),
):
    try:
        return await service.create_milestone(db, data)
    except ForeignKeyError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/{milestone_id}", response_model=MilestoneDTO)
async def update_milestone(
    milestone_id: UUID,
    data: MilestoneUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoMilestoneService = Depends(get_milestone_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_milestone(db, milestone_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Milestone {milestone_id} not found")
    return result


@router.delete("/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(
    milestone_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoMilestoneService = Depends(get_milestone_service),
    _: str = Depends(verify_service_key),
):
    deleted = await service.delete_milestone(db, milestone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Milestone {milestone_id} not found")
