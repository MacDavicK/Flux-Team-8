"""User API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_user_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.schemas.user import UserCreateDTO, UserDTO, UserUpdateDTO
from dao_service.services.dao_user_service import DaoUserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=PaginatedResponse[UserDTO])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoUserService = Depends(get_user_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_users(db, skip=skip, limit=limit)
    total = await service.count_users(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/{user_id}", response_model=UserDTO)
async def get_user(
    user_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoUserService = Depends(get_user_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_user(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return result


@router.post("/", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoUserService = Depends(get_user_service),
    _: str = Depends(verify_service_key),
):
    return await service.create_user(db, data)


@router.patch("/{user_id}", response_model=UserDTO)
async def update_user(
    user_id: UUID,
    data: UserUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoUserService = Depends(get_user_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_user(db, user_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return result


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoUserService = Depends(get_user_service),
    _: str = Depends(verify_service_key),
):
    deleted = await service.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
