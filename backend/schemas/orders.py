import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    po_number: str | None = None
    vendor_name: str | None = None
    total_amount: float | None = None
    currency: str | None = None
    status: str
    issue_tags: list[str] = []
    created_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderSummary]
    total: int
    page: int
    page_size: int


class ValidationCheckDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_type: str
    result: str
    details: dict[str, Any] | None = None


class IssueTagDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tag: str
    severity: str
    description: str | None = None


class EmailDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    direction: str
    email_type: str
    sender: str
    recipient: str
    subject: str | None = None
    sent_at: datetime


class ProcessingLogDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step: str
    status: str
    duration_ms: int | None = None


class ReviewDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: str
    comment: str | None = None
    decided_at: datetime


class OrderDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    po_number: str | None = None
    po_date: str | None = None
    vendor_name: str | None = None
    vendor_contact: str | None = None
    requester_name: str | None = None
    requester_department: str | None = None
    line_items: dict[str, Any] | None = None
    total_amount: float | None = None
    currency: str | None = None
    delivery_date: str | None = None
    payment_terms: str | None = None
    status: str
    confidence_score: float | None = None
    original_filename: str | None = None
    sender_email: str | None = None
    created_at: datetime
    updated_at: datetime
    validation_results: list[ValidationCheckDetail] = []
    issue_tags: list[IssueTagDetail] = []
    emails: list[EmailDetail] = []
    processing_logs: list[ProcessingLogDetail] = []
    review: ReviewDetail | None = None
