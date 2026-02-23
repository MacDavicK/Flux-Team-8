"""Goal ORM model."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.conversation_model import Conversation
    from dao_service.models.milestone_model import Milestone
    from dao_service.models.task_model import Task
    from dao_service.models.user_model import User


class Goal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "goals"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timeline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="active", server_default="active")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="goals")
    milestones: Mapped[List["Milestone"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship(back_populates="goal", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
