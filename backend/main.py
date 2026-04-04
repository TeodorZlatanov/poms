import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from loguru import logger

from api.routes.analytics import router as analytics_router
from api.routes.orders import router as orders_router
from api.routes.reviews import router as reviews_router
from api.routes.webhook import router as webhook_router
from core.observability import setup_logging
from services.email import email_service
from services.knowledge import knowledge_service
from services.poller import start_polling


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Set up logging
    setup_logging()
    logger.info("Starting POMS backend...")

    # Run Alembic migrations
    logger.info("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    await asyncio.get_event_loop().run_in_executor(None, command.upgrade, alembic_cfg, "head")
    logger.info("Database migrations complete.")

    # Connect to RAG knowledge base (must be pre-built via scripts.ingest_knowledge)
    await knowledge_service.initialize()

    # Authenticate email service and start polling
    poller_task = None
    try:
        await email_service.authenticate()
        logger.info("Email service authenticated.")
        poller_task = asyncio.create_task(start_polling())
        logger.info("Gmail polling started.")
    except Exception:
        logger.warning("Email service not configured — polling disabled")

    yield

    if poller_task:
        poller_task.cancel()
        logger.info("Gmail polling stopped.")
    logger.info("Shutting down POMS backend...")


app = FastAPI(
    title="POMS — Purchase Order Management System",
    description="AI-powered purchase order processing pipeline",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(webhook_router)
app.include_router(orders_router)
app.include_router(reviews_router)
app.include_router(analytics_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
