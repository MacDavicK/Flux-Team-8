"""Demo flag API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from dao_service.api.deps import get_db, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.dao.dao_registry import get_demo_flag_dao
from dao_service.schemas.demo_flag import DemoFlagCreateDTO, DemoFlagDTO

router = APIRouter(prefix="/demo-flags", tags=["demo-flags"])


@router.get("/{user_id}", response_model=DemoFlagDTO)
async def get_demo_flags(
    user_id: UUID,
    db: DatabaseSession = Depends(get_db),
    _: str = Depends(verify_service_key),
):
    dao = get_demo_flag_dao()
    result = await dao.get_by_user_id(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Demo flags for user {user_id} not found")
    return result


@router.put("/{user_id}", response_model=DemoFlagDTO)
async def upsert_demo_flags(
    user_id: UUID,
    data: DemoFlagCreateDTO,
    db: DatabaseSession = Depends(get_db),
    _: str = Depends(verify_service_key),
):
    # Ensure user_id in path matches body
    if data.user_id != user_id:
        raise HTTPException(status_code=400, detail="user_id in path and body must match")
    dao = get_demo_flag_dao()
    return await dao.upsert(db, data)
