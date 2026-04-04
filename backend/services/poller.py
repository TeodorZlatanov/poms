import asyncio

from loguru import logger

from core.config import settings
from core.database import async_session_factory
from services.email import email_service
from services.pipeline import process_email

_shutdown = False


def request_shutdown() -> None:
    global _shutdown  # noqa: PLW0603
    _shutdown = True


async def poll_once() -> int:
    """Single poll iteration. Returns count of emails processed."""
    payloads = await email_service.fetch_new_emails()
    if not payloads:
        return 0

    processed = 0
    for payload in payloads:
        try:
            async with async_session_factory() as session:
                await process_email(payload, session)
                processed += 1
        except Exception:
            logger.exception("Failed to process polled email from {}", payload.from_address)

    return processed


async def start_polling() -> None:
    """Infinite polling loop. Runs as a background task."""
    logger.info("Gmail poller started — interval={}s", settings.poll_interval_seconds)

    while not _shutdown:
        try:
            count = await poll_once()
            if count:
                logger.info("Polled and processed {} emails", count)
        except Exception:
            logger.exception("Error during poll cycle")

        await asyncio.sleep(settings.poll_interval_seconds)

    logger.info("Gmail poller stopped")
