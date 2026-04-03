import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Index
from sqlmodel import Column, Field, SQLModel


class ValidationCheck(SQLModel, table=True):
    __tablename__ = "validation_checks"
    __table_args__ = (Index("ix_validation_checks_order_id", "order_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="purchase_orders.id")
    check_type: str = Field(max_length=20)
    result: str = Field(max_length=20)
    details: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IssueTag(SQLModel, table=True):
    __tablename__ = "issue_tags"
    __table_args__ = (Index("ix_issue_tags_order_id", "order_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="purchase_orders.id")
    tag: str = Field(max_length=30)
    severity: str = Field(max_length=10)
    description: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
