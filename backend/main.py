import asyncio
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from loguru import logger

from api.routes.webhook import router as webhook_router
from core.observability import setup_logging
from services.knowledge import knowledge_base


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

    # Initialize knowledge base
    logger.info("Initializing knowledge base...")
    await knowledge_base.initialize()
    logger.info("Knowledge base ready.")

    yield

    logger.info("Shutting down POMS backend...")


app = FastAPI(
    title="POMS — Purchase Order Management System",
    description="AI-powered purchase order processing pipeline",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(webhook_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
