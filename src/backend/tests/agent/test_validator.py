from agent.validator import validate_completeness
from schemas.extraction import LineItem, PurchaseOrderExtraction, RequesterInfo, VendorInfo


class TestValidateCompleteness:
    async def test_complete_po_passes(self):
        extraction = PurchaseOrderExtraction(
            po_number="PO-001",
            vendor=VendorInfo(name="Test Vendor", contact="test@test.com"),
            requester=RequesterInfo(name="John", department="Engineering"),
            line_items=[LineItem(description="Widget", sku="SKU-001", quantity=10, unit_price=5.0)],
            total_amount=100.0,
            currency="EUR",
            delivery_date="2025-01-01",
            payment_terms="Net 30",
        )
        result = await validate_completeness(extraction)
        assert result.result.value == "PASS"
        assert len([t for t in result.tags if t.severity.value == "HARD"]) == 0

    async def test_missing_po_number_hard_tag(self):
        extraction = PurchaseOrderExtraction(
            vendor=VendorInfo(name="Test Vendor"),
            line_items=[LineItem(description="Widget", quantity=10)],
            total_amount=100.0,
            currency="EUR",
            delivery_date="2025-01-01",
        )
        result = await validate_completeness(extraction)
        hard_tags = [t for t in result.tags if t.severity.value == "HARD"]
        assert any(t.tag.value == "MISSING_FIELD" for t in hard_tags)

    async def test_missing_vendor_contact_soft_tag(self):
        extraction = PurchaseOrderExtraction(
            po_number="PO-001",
            vendor=VendorInfo(name="Test Vendor"),
            line_items=[LineItem(description="Widget", quantity=10)],
            total_amount=100.0,
            currency="EUR",
            delivery_date="2025-01-01",
        )
        result = await validate_completeness(extraction)
        soft_tags = [t for t in result.tags if t.severity.value == "SOFT"]
        assert any(t.tag.value == "MISSING_FIELD" for t in soft_tags)

    async def test_empty_line_items_hard_tag(self):
        extraction = PurchaseOrderExtraction(
            po_number="PO-001",
            vendor=VendorInfo(name="Test Vendor"),
            line_items=[],
            total_amount=100.0,
            currency="EUR",
            delivery_date="2025-01-01",
        )
        result = await validate_completeness(extraction)
        hard_tags = [t for t in result.tags if t.severity.value == "HARD"]
        assert any(t.tag.value == "MISSING_FIELD" for t in hard_tags)

    async def test_missing_total_amount_hard_tag(self):
        extraction = PurchaseOrderExtraction(
            po_number="PO-001",
            vendor=VendorInfo(name="Test Vendor"),
            line_items=[LineItem(description="Widget", quantity=10)],
            currency="EUR",
            delivery_date="2025-01-01",
        )
        result = await validate_completeness(extraction)
        hard_tags = [t for t in result.tags if t.severity.value == "HARD"]
        assert any("total_amount" in t.description for t in hard_tags)

    async def test_all_hard_fields_missing(self):
        extraction = PurchaseOrderExtraction(
            vendor=VendorInfo(name=""),
            line_items=[],
        )
        result = await validate_completeness(extraction)
        assert result.result.value == "FAIL"
        hard_tags = [t for t in result.tags if t.severity.value == "HARD"]
        assert (
            len(hard_tags) >= 4
        )  # po_number, vendor.name, line_items, total_amount, currency, delivery_date
