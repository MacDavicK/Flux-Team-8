"""Goal ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.task_model import Task
    from dao_service.models.user_model import User


class Goal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "goals"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    class_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True)
    status: Mapped[str] = mapped_column(Text, default="active", server_default="active")
    parent_goal_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id"), nullable=True
    )
    pipeline_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    target_weeks: Mapped[int] = mapped_column(Integer, default=6, server_default="6")
    plan_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="goals")
    tasks: Mapped[List["Task"]] = relationship(back_populates="goal")
    parent_goal: Mapped[Optional["Goal"]] = relationship(
        "Goal", remote_side="Goal.id", back_populates="child_goals"
    )
    child_goals: Mapped[List["Goal"]] = relationship("Goal", back_populates="parent_goal")
