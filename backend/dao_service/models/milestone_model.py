"""Milestone ORM model."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.goal_model import Goal
    from dao_service.models.task_model import Task


class Milestone(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "milestones"

    goal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", server_default="pending")

    # Relationships
    goal: Mapped["Goal"] = relationship(back_populates="milestones")
    tasks: Mapped[List["Task"]] = relationship(back_populates="milestone", cascade="all, delete-orphan")
