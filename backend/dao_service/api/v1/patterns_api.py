"""Pattern API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_pattern_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.schemas.pattern import PatternCreateDTO, PatternDTO, PatternUpdateDTO
from dao_service.services.dao_pattern_service import DaoPatternService

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/", response_model=PaginatedResponse[PatternDTO])
async def list_patterns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoPatternService = Depends(get_pattern_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_patterns(db, skip=skip, limit=limit)
    total = await service.count_patterns(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/{pattern_id}", response_model=PatternDTO)
async def get_pattern(
    pattern_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoPatternService = Depends(get_pattern_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_pattern(db, pattern_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
    return result


@router.post("/", response_model=PatternDTO, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    data: PatternCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoPatternService = Depends(get_pattern_service),
    _: str = Depends(verify_service_key),
):
    return await service.create_pattern(db, data)


@router.patch("/{pattern_id}", response_model=PatternDTO)
async def update_pattern(
    pattern_id: UUID,
    data: PatternUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoPatternService = Depends(get_pattern_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_pattern(db, pattern_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
    return result


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoPatternService = Depends(get_pattern_service),
    _: str = Depends(verify_service_key),
):
    deleted = await service.delete_pattern(db, pattern_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")
