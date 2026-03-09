"""Message ORM model — voice conversation transcript messages."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.conversation_model import Conversation


class Message(Base, UUIDMixin, TimestampMixin):
    """Transcript message linked to a conversation (voice or text)."""

    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    input_modality: Mapped[str] = mapped_column(Text, default="text", server_default="text")
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict, server_default="{}")

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
