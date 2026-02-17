"""User ORM model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.conversation_model import Conversation
    from dao_service.models.demo_flag_model import DemoFlag
    from dao_service.models.goal_model import Goal
    from dao_service.models.task_model import Task


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, server_default="{}")
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Relationships
    goals: Mapped[List["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    demo_flag: Mapped[Optional["DemoFlag"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
