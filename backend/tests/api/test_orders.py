import uuid

from models import IssueTag, ProcessingLog, PurchaseOrder, ValidationCheck


class TestListOrders:
    async def test_list_orders_empty(self, client):
        response = await client.get("/api/orders/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    async def test_list_orders_with_data(self, client, db_session):
        order = PurchaseOrder(
            id=uuid.uuid4(),
            po_number="PO-2024-001",
            vendor_name="Acme Corp",
            total_amount=1500.00,
            currency="USD",
            status="APPROVED",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.get("/api/orders/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["po_number"] == "PO-2024-001"
        assert data["items"][0]["vendor_name"] == "Acme Corp"

    async def test_list_orders_filter_by_status(self, client, db_session):
        for i, status in enumerate(["APPROVED", "APPROVED", "PENDING_REVIEW"]):
            order = PurchaseOrder(
                id=uuid.uuid4(),
                po_number=f"PO-{i}",
                status=status,
                vendor_name=f"Vendor {i}",
            )
            db_session.add(order)
        await db_session.flush()

        response = await client.get("/api/orders/", params={"status": "APPROVED"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["status"] == "APPROVED" for item in data["items"])

    async def test_list_orders_filter_by_vendor(self, client, db_session):
        for name in ["Acme Corp", "Acme Industries", "Globex Inc"]:
            db_session.add(PurchaseOrder(id=uuid.uuid4(), vendor_name=name, status="APPROVED"))
        await db_session.flush()

        response = await client.get("/api/orders/", params={"vendor": "acme"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_list_orders_pagination(self, client, db_session):
        for i in range(25):
            db_session.add(
                PurchaseOrder(id=uuid.uuid4(), po_number=f"PO-{i:03d}", status="APPROVED")
            )
        await db_session.flush()

        response = await client.get("/api/orders/", params={"page": 1, "page_size": 20})
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 20

        response2 = await client.get("/api/orders/", params={"page": 2, "page_size": 20})
        data2 = response2.json()
        assert len(data2["items"]) == 5


class TestGetOrder:
    async def test_get_order_detail(self, client, db_session):
        order_id = uuid.uuid4()
        order = PurchaseOrder(
            id=order_id,
            po_number="PO-DETAIL-001",
            vendor_name="Detail Vendor",
            total_amount=2000.00,
            currency="EUR",
            status="PENDING_REVIEW",
            sender_email="test@example.com",
        )
        db_session.add(order)
        db_session.add(
            ValidationCheck(
                order_id=order_id,
                check_type="VENDOR",
                result="PASS",
                details={"match": True},
            )
        )
        db_session.add(
            IssueTag(
                order_id=order_id,
                tag="PRICE_MISMATCH",
                severity="SOFT",
                description="10% over catalog price",
            )
        )
        db_session.add(
            ProcessingLog(
                order_id=order_id,
                step="classification",
                status="COMPLETED",
                duration_ms=120,
            )
        )
        await db_session.flush()

        response = await client.get(f"/api/orders/{order_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["po_number"] == "PO-DETAIL-001"
        assert len(data["validation_results"]) == 1
        assert len(data["issue_tags"]) == 1
        assert data["issue_tags"][0]["tag"] == "PRICE_MISMATCH"
        assert len(data["processing_logs"]) == 1
        assert data["review"] is None

    async def test_get_order_not_found(self, client):
        random_id = uuid.uuid4()
        response = await client.get(f"/api/orders/{random_id}")
        assert response.status_code == 404
