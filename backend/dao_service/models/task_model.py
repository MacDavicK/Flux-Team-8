"""Task ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from dao_service.models.goal_model import Goal
    from dao_service.models.notification_log_model import NotificationLog
    from dao_service.models.user_model import User


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="pending", server_default="pending")
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trigger_type: Mapped[str] = mapped_column(Text, default="time", server_default="time")
    location_trigger: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    whatsapp_sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    call_sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shared_with_goal_ids: Mapped[Optional[List[UUID]]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")
    goal: Mapped["Goal"] = relationship(back_populates="tasks")
    notification_logs: Mapped[List["NotificationLog"]] = relationship(back_populates="task")
