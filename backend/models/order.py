import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index
from sqlmodel import Column, Field, SQLModel


class PurchaseOrder(SQLModel, table=True):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_purchase_orders_status", "status"),
        Index("ix_purchase_orders_created_at", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    po_number: str | None = Field(default=None, max_length=100)
    po_date: str | None = Field(default=None, max_length=20)
    vendor_name: str | None = Field(default=None, max_length=255)
    vendor_contact: str | None = Field(default=None, max_length=255)
    requester_name: str | None = Field(default=None, max_length=255)
    requester_department: str | None = Field(default=None, max_length=100)
    line_items: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    total_amount: float | None = Field(default=None)
    currency: str | None = Field(default=None, max_length=10)
    delivery_date: str | None = Field(default=None, max_length=20)
    payment_terms: str | None = Field(default=None, max_length=50)
    status: str = Field(default="PROCESSING", max_length=20)
    confidence_score: float | None = Field(default=None)
    original_filename: str | None = Field(default=None, max_length=500)
    sender_email: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
