"""Task ORM model — the most complex entity with calendar_event_id."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base, TimestampMixin, UUIDMixin
from dao_service.models.enums import TaskPriorityEnum, TaskStateEnum, TriggerTypeEnum

if TYPE_CHECKING:
    from dao_service.models.goal_model import Goal
    from dao_service.models.milestone_model import Milestone
    from dao_service.models.user_model import User


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    milestone_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("milestones.id", ondelete="CASCADE"), nullable=True
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    state: Mapped[TaskStateEnum] = mapped_column(
        Enum(
            TaskStateEnum,
            name="task_state",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=TaskStateEnum.SCHEDULED,
        server_default="scheduled",
    )
    priority: Mapped[TaskPriorityEnum] = mapped_column(
        Enum(
            TaskPriorityEnum,
            name="task_priority",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=TaskPriorityEnum.STANDARD,
        server_default="standard",
    )
    trigger_type: Mapped[TriggerTypeEnum] = mapped_column(
        Enum(
            TriggerTypeEnum,
            name="trigger_type",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        default=TriggerTypeEnum.TIME,
        server_default="time",
    )

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tasks")
    goal: Mapped["Goal"] = relationship(back_populates="tasks")
    milestone: Mapped[Optional["Milestone"]] = relationship(back_populates="tasks")
