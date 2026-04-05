import asyncio

from fastapi import APIRouter, Depends
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import async_session_factory, get_session
from schemas.webhook import WebhookEmailPayload, WebhookResponse
from services.pipeline import create_placeholder_orders, process_placeholders

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/email", response_model=WebhookResponse, status_code=202)
async def ingest_email(
    payload: WebhookEmailPayload,
    session: AsyncSession = Depends(get_session),
):
    """Create PROCESSING placeholder orders synchronously so they show up in the
    dashboard immediately, then run the full pipeline in a background task.
    """
    batch_id, placeholder_ids = await create_placeholder_orders(payload, session)
    await session.commit()

    async def _run_pipeline() -> None:
        async with async_session_factory() as bg_session:
            try:
                await process_placeholders(payload, batch_id, placeholder_ids, bg_session)
            except Exception:
                logger.exception("Background pipeline failed for batch {}", batch_id)
                await bg_session.rollback()

    asyncio.create_task(_run_pipeline())

    return WebhookResponse(
        message="Email received and queued for processing",
        tracking_id=str(batch_id),
    )
