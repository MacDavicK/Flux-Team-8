"""DemoFlag ORM model — one row per user."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dao_service.models.base import Base

if TYPE_CHECKING:
    from dao_service.models.user_model import User


class DemoFlag(Base):
    __tablename__ = "demo_flags"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    virtual_now: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    escalation_speed: Mapped[float] = mapped_column(
        Float, default=1.0, server_default="1.0"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="demo_flag")
