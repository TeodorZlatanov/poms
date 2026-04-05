import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def webhook_client():
    """Client that doesn't need a real DB — overrides session dependency."""
    from core.database import get_session
    from main import app

    async def mock_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = mock_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestWebhookEndpoint:
    @patch("api.routes.webhook.process_placeholders", new_callable=AsyncMock)
    @patch("api.routes.webhook.create_placeholder_orders", new_callable=AsyncMock)
    async def test_valid_payload_returns_202(
        self, mock_create, _mock_process, webhook_client, sample_email_payload
    ):
        mock_create.return_value = (uuid.uuid4(), [uuid.uuid4()])
        response = await webhook_client.post("/api/webhook/email", json=sample_email_payload())
        assert response.status_code == 202
        data = response.json()
        assert "tracking_id" in data
        assert data["message"] == "Email received and queued for processing"

    async def test_missing_fields_returns_422(self, webhook_client):
        response = await webhook_client.post("/api/webhook/email", json={"subject": "test"})
        assert response.status_code == 422

    @patch("api.routes.webhook.process_placeholders", new_callable=AsyncMock)
    @patch("api.routes.webhook.create_placeholder_orders", new_callable=AsyncMock)
    async def test_empty_attachments_accepted(
        self, mock_create, _mock_process, webhook_client, sample_email_payload
    ):
        mock_create.return_value = (uuid.uuid4(), [])
        response = await webhook_client.post(
            "/api/webhook/email", json=sample_email_payload(attachments=[])
        )
        assert response.status_code == 202
