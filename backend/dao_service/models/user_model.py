"""User ORM model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.conversation_model import Conversation
    from dao_service.models.goal_model import Goal
    from dao_service.models.task_model import Task
    from dao_service.models.pattern_model import Pattern


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    profile: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    notification_preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    goals: Mapped[List["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    patterns: Mapped[List["Pattern"]] = relationship(back_populates="user", cascade="all, delete-orphan")
