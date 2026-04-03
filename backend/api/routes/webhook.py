from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_session
from schemas.webhook import WebhookEmailPayload, WebhookResponse
from services.pipeline import process_email

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/email", response_model=WebhookResponse, status_code=202)
async def ingest_email(
    payload: WebhookEmailPayload,
    session: AsyncSession = Depends(get_session),
):
    tracking_id = await process_email(payload, session)
    return WebhookResponse(
        message="Email received and queued for processing",
        tracking_id=str(tracking_id),
    )
