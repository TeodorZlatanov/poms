import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlmodel import Column, Field, SQLModel

from core.time import utc_now


class ApprovedVendor(SQLModel, table=True):
    __tablename__ = "approved_vendors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    vendor_id: str = Field(max_length=20, unique=True)
    name: str = Field(max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    contract_status: str = Field(max_length=20)
    contract_expiry_date: str | None = Field(default=None, max_length=20)
    address: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    payment_terms: str = Field(max_length=50)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ProductCatalog(SQLModel, table=True):
    __tablename__ = "product_catalog"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku: str = Field(max_length=30, unique=True)
    description: str = Field(max_length=500)
    category: str = Field(max_length=100)
    unit_price: float
    currency: str = Field(max_length=10)
    unit_of_measure: str = Field(max_length=20)
    min_order_quantity: int
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ProcurementPolicy(SQLModel, table=True):
    __tablename__ = "procurement_policies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    policy_type: str = Field(max_length=50)
    department: str | None = Field(default=None, max_length=100)
    threshold_value: float | None = Field(default=None)
    allowed_values: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    description: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
