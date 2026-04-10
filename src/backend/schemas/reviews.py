import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class ReviewRequest(BaseModel):
    decision: str
    comment: str | None = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v.lower() not in ("approve", "reject"):
            msg = "Decision must be 'approve' or 'reject'"
            raise ValueError(msg)
        return v.lower()


class ReviewResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    decision: str
    comment: str | None = None
    decided_at: datetime
    email_sent: bool
