"""Conversation API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_conversation_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.conversation import (
    ConversationCreateDTO,
    ConversationDTO,
    ConversationUpdateDTO,
    VoiceConversationUpdateDTO,
)
from dao_service.schemas.pagination import PaginatedResponse
from dao_service.services.dao_conversation_service import DaoConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=PaginatedResponse[ConversationDTO])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: DatabaseSession = Depends(get_db),
    service: DaoConversationService = Depends(get_conversation_service),
    _: str = Depends(verify_service_key),
):
    items = await service.get_conversations(db, skip=skip, limit=limit)
    total = await service.count_conversations(db)
    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0,
    )


@router.get("/{conversation_id}", response_model=ConversationDTO)
async def get_conversation(
    conversation_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoConversationService = Depends(get_conversation_service),
    _: str = Depends(verify_service_key),
):
    result = await service.get_conversation(db, conversation_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return result


@router.post("/", response_model=ConversationDTO, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoConversationService = Depends(get_conversation_service),
    _: str = Depends(verify_service_key),
):
    return await service.create_conversation(db, data)


@router.patch("/{conversation_id}", response_model=ConversationDTO)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoConversationService = Depends(get_conversation_service),
    _: str = Depends(verify_service_key),
):
    result = await service.update_conversation(db, conversation_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return result


@router.patch("/{conversation_id}/voice", response_model=ConversationDTO)
async def update_conversation_voice(
    conversation_id: UUID,
    data: VoiceConversationUpdateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoConversationService = Depends(get_conversation_service),
    _: str = Depends(verify_service_key),
):
    """Update voice-specific fields when closing a voice session."""
    result = await service.update_conversation_voice(db, conversation_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return result
