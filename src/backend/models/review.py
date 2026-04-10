import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index
from sqlmodel import Field, SQLModel

from core.time import utc_now


class ReviewDecision(SQLModel, table=True):
    __tablename__ = "review_decisions"
    __table_args__ = (Index("ix_review_decisions_order_id", "order_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="purchase_orders.id")
    decision: str = Field(max_length=20)
    comment: str | None = Field(default=None, max_length=1000)
    decided_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
