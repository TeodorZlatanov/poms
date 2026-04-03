import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class EmailLog(SQLModel, table=True):
    __tablename__ = "email_logs"
    __table_args__ = (Index("ix_email_logs_order_id", "order_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID | None = Field(default=None, foreign_key="purchase_orders.id")
    direction: str = Field(max_length=10)
    email_type: str = Field(max_length=20)
    sender: str = Field(max_length=255)
    recipient: str = Field(max_length=255)
    subject: str | None = Field(default=None, max_length=500)
    sent_at: datetime = Field(default_factory=datetime.utcnow)
