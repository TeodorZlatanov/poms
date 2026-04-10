import uuid

from models import IssueTag, ProcessingLog, PurchaseOrder


class TestAnalytics:
    async def test_analytics_empty(self, client):
        response = await client.get("/api/analytics/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 0
        assert data["approval_rate"] == 0.0
        assert data["common_tags"] == []
        assert data["avg_processing_time_ms"] == 0.0

    async def test_analytics_with_data(self, client, db_session):
        # Create orders with various statuses
        orders = [
            PurchaseOrder(id=uuid.uuid4(), po_number=f"PO-{i}", status=status)
            for i, status in enumerate(
                ["APPROVED", "APPROVED", "APPROVED", "PENDING_REVIEW", "REJECTED"]
            )
        ]
        for order in orders:
            db_session.add(order)

        # Add issue tags
        for order in orders[3:]:
            db_session.add(
                IssueTag(
                    order_id=order.id,
                    tag="PRICE_MISMATCH",
                    severity="SOFT",
                    description="Price too high",
                )
            )
        db_session.add(
            IssueTag(
                order_id=orders[4].id,
                tag="UNKNOWN_VENDOR",
                severity="HARD",
                description="Not in registry",
            )
        )

        # Add processing logs
        for order in orders:
            db_session.add(
                ProcessingLog(
                    order_id=order.id,
                    step="classification",
                    status="COMPLETED",
                    duration_ms=100,
                )
            )
            db_session.add(
                ProcessingLog(
                    order_id=order.id,
                    step="extraction",
                    status="COMPLETED",
                    duration_ms=200,
                )
            )

        await db_session.flush()

        response = await client.get("/api/analytics/")
        assert response.status_code == 200
        data = response.json()

        assert data["total_processed"] == 5
        assert data["by_status"]["APPROVED"] == 3
        assert data["by_status"]["PENDING_REVIEW"] == 1
        assert data["by_status"]["REJECTED"] == 1
        assert data["approval_rate"] == 0.6

        # Tags
        assert len(data["common_tags"]) == 2
        tag_names = {t["tag"] for t in data["common_tags"]}
        assert "PRICE_MISMATCH" in tag_names
        assert "UNKNOWN_VENDOR" in tag_names

        # Avg processing time: each order has 100+200=300ms, avg=300
        assert data["avg_processing_time_ms"] == 300.0

        # Volume by day
        assert len(data["volume_by_day"]) >= 1
