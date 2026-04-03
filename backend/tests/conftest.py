import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import settings
from core.database import get_session

# Test database URL: append _test to the database name
TEST_DB_URL = settings.database_url.rsplit("/", 1)[0] + "/poms_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session(setup_db):  # noqa: ARG001
    async with test_session_factory() as session, session.begin():
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    from main import app

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_email_payload():
    """Factory for valid webhook payloads."""

    def _make(**overrides):
        base = {
            "from": "sender@example.com",
            "subject": "Purchase Order PO-2024-0047",
            "body": "Please find attached our purchase order.",
            "attachments": [
                {
                    "filename": "po_2024_0047.pdf",
                    "content_type": "application/pdf",
                    "data": "base64encodedcontent",
                }
            ],
            "received_at": "2024-11-15T10:30:00Z",
        }
        base.update(overrides)
        return base

    return _make
