from pydantic import BaseModel, ConfigDict, Field


class AttachmentPayload(BaseModel):
    filename: str
    content_type: str
    data: str  # base64-encoded file content


class WebhookEmailPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_address: str = Field(alias="from")
    subject: str
    body: str
    attachments: list[AttachmentPayload]
    received_at: str  # ISO 8601 datetime string


class WebhookResponse(BaseModel):
    message: str
    tracking_id: str
