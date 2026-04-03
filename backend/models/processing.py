import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index
from sqlmodel import Column, Field, SQLModel


class ProcessingLog(SQLModel, table=True):
    __tablename__ = "processing_logs"
    __table_args__ = (Index("ix_processing_logs_order_id", "order_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="purchase_orders.id")
    step: str = Field(max_length=50)
    status: str = Field(max_length=20)
    duration_ms: int | None = Field(default=None)
    metadata_: dict[str, Any] | None = Field(default=None, sa_column=Column("metadata", JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
