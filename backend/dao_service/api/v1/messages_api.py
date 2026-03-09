"""REST endpoints for messages."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dao_service.api.deps import get_db, get_message_service, verify_service_key
from dao_service.core.database import DatabaseSession
from dao_service.schemas.message import MessageCreateDTO, MessageDTO
from dao_service.services.dao_message_service import DaoMessageService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/", response_model=MessageDTO, status_code=status.HTTP_201_CREATED)
async def create_message(
    data: MessageCreateDTO,
    db: DatabaseSession = Depends(get_db),
    service: DaoMessageService = Depends(get_message_service),
    _: str = Depends(verify_service_key),
):
    """Create a new message linked to a conversation."""
    return await service.create_message(db, data)


@router.get("/", response_model=List[MessageDTO])
async def list_messages(
    conversation_id: UUID = Query(..., description="Filter messages by conversation"),
    db: DatabaseSession = Depends(get_db),
    service: DaoMessageService = Depends(get_message_service),
    _: str = Depends(verify_service_key),
):
    """List messages for a conversation, ordered chronologically."""
    return await service.get_messages_for_conversation(db, conversation_id)


@router.get("/{message_id}", response_model=MessageDTO)
async def get_message(
    message_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoMessageService = Depends(get_message_service),
    _: str = Depends(verify_service_key),
):
    """Get a single message by ID."""
    result = await service.get_message(db, message_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
    return result


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: UUID,
    db: DatabaseSession = Depends(get_db),
    service: DaoMessageService = Depends(get_message_service),
    _: str = Depends(verify_service_key),
):
    """Delete a message by ID."""
    deleted = await service.delete_message(db, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
