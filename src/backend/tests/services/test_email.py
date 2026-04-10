import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import EmailLog, PurchaseOrder
from services.email import EmailService


def _email_logs_from_adds(session: MagicMock) -> list[EmailLog]:
    """Extract EmailLog objects from session.add() calls."""
    return [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], EmailLog)
    ]


@pytest.fixture
def email_svc():
    """Create an EmailService with authentication flag set."""
    svc = EmailService()
    svc._authenticated = True
    return svc


@pytest.fixture
def sample_order():
    return PurchaseOrder(
        id=uuid.uuid4(),
        po_number="PO-TEST-001",
        vendor_name="Test Vendor",
        total_amount=1000.00,
        currency="USD",
        delivery_date="2024-12-01",
        status="APPROVED",
        sender_email="buyer@example.com",
    )


class TestEmailService:
    @patch("services.email.asyncio.to_thread", new_callable=AsyncMock)
    async def test_send_batch_summary_all_approved_sends_confirmation(
        self, mock_thread, email_svc, sample_order
    ):
        mock_thread.return_value = {"id": "msg123"}
        session = MagicMock()
        session.add = MagicMock()

        # Need to set _service so send_email doesn't fail building the API call
        email_svc._service = MagicMock()

        await email_svc.send_batch_summary([sample_order], session)

        mock_thread.assert_called_once()
        email_logs = _email_logs_from_adds(session)
        assert len(email_logs) == 1
        assert email_logs[0].email_type == "CONFIRMATION"
        assert email_logs[0].recipient == "buyer@example.com"
        assert "PO-TEST-001" in email_logs[0].subject

    @patch("services.email.asyncio.to_thread", new_callable=AsyncMock)
    async def test_send_batch_summary_with_review_sends_acknowledgment(
        self, mock_thread, email_svc, sample_order
    ):
        mock_thread.return_value = {"id": "msg123"}
        sample_order.status = "PENDING_REVIEW"
        session = MagicMock()
        session.add = MagicMock()
        email_svc._service = MagicMock()

        await email_svc.send_batch_summary([sample_order], session)

        mock_thread.assert_called_once()
        email_logs = _email_logs_from_adds(session)
        assert len(email_logs) == 1
        assert email_logs[0].email_type == "ACKNOWLEDGMENT"

    @patch("services.email.asyncio.to_thread", new_callable=AsyncMock)
    async def test_send_decision_approve(self, mock_thread, email_svc, sample_order):
        mock_thread.return_value = {"id": "msg123"}
        session = MagicMock()
        session.add = MagicMock()
        # Mock session.exec for tag query (not needed for approve, but called for reject)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.exec = AsyncMock(return_value=mock_result)
        email_svc._service = MagicMock()

        await email_svc.send_decision(sample_order, "approve", "Looks good", session)

        mock_thread.assert_called_once()
        session.add.assert_called_once()
        email_log = session.add.call_args[0][0]
        assert email_log.email_type == "CONFIRMATION"

    @patch("services.email.asyncio.to_thread", new_callable=AsyncMock)
    async def test_send_decision_reject(self, mock_thread, email_svc, sample_order):
        mock_thread.return_value = {"id": "msg123"}
        session = MagicMock()
        session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.exec = AsyncMock(return_value=mock_result)
        email_svc._service = MagicMock()

        await email_svc.send_decision(sample_order, "reject", "Vendor issue", session)

        mock_thread.assert_called_once()
        session.add.assert_called_once()
        email_log = session.add.call_args[0][0]
        assert email_log.email_type == "REJECTION"

    async def test_send_skipped_when_not_authenticated(self, sample_order):
        svc = EmailService()
        session = MagicMock()
        session.add = MagicMock()
        # Should not raise
        await svc.send_email(
            to="test@example.com",
            subject="test",
            body="test",
            order_id=sample_order.id,
            session=session,
        )
        session.add.assert_not_called()
