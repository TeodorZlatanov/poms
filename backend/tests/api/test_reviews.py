import uuid
from unittest.mock import AsyncMock, patch

from models import PurchaseOrder


class TestSubmitReview:
    @patch("api.routes.reviews.email_service")
    async def test_approve_pending_order(self, mock_email, client, db_session):
        mock_email.send_decision = AsyncMock()
        order = PurchaseOrder(
            id=uuid.uuid4(),
            po_number="PO-REVIEW-001",
            vendor_name="Review Vendor",
            total_amount=5000.00,
            currency="USD",
            status="PENDING_REVIEW",
            sender_email="submitter@example.com",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.post(
            f"/api/reviews/{order.id}",
            json={"decision": "approve", "comment": "Looks good"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "APPROVE"
        assert data["comment"] == "Looks good"
        assert data["order_id"] == str(order.id)

    @patch("api.routes.reviews.email_service")
    async def test_reject_pending_order(self, mock_email, client, db_session):
        mock_email.send_decision = AsyncMock()
        order = PurchaseOrder(
            id=uuid.uuid4(),
            po_number="PO-REVIEW-002",
            status="PENDING_REVIEW",
            sender_email="submitter@example.com",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.post(
            f"/api/reviews/{order.id}",
            json={"decision": "reject", "comment": "Vendor not approved"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "REJECT"
        assert data["comment"] == "Vendor not approved"

    async def test_review_not_found(self, client):
        response = await client.post(
            f"/api/reviews/{uuid.uuid4()}",
            json={"decision": "approve"},
        )
        assert response.status_code == 404

    @patch("api.routes.reviews.email_service")
    async def test_review_already_approved(self, mock_email, client, db_session):  # noqa: ARG002
        order = PurchaseOrder(
            id=uuid.uuid4(),
            po_number="PO-DONE",
            status="APPROVED",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.post(
            f"/api/reviews/{order.id}",
            json={"decision": "approve"},
        )
        assert response.status_code == 400

    async def test_review_invalid_decision(self, client, db_session):
        order = PurchaseOrder(
            id=uuid.uuid4(),
            po_number="PO-INV",
            status="PENDING_REVIEW",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.post(
            f"/api/reviews/{order.id}",
            json={"decision": "invalid"},
        )
        assert response.status_code == 422

    @patch("api.routes.reviews.email_service")
    async def test_approve_rejected_order(self, mock_email, client, db_session):
        mock_email.send_decision = AsyncMock()
        order = PurchaseOrder(
            id=uuid.uuid4(),
            po_number="PO-REJ",
            status="REJECTED",
            sender_email="test@example.com",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.post(
            f"/api/reviews/{order.id}",
            json={"decision": "approve"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "APPROVE"
