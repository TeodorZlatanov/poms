from unittest.mock import AsyncMock, MagicMock, patch

from schemas.webhook import AttachmentPayload, WebhookEmailPayload


def _make_payload(**overrides):
    base = {
        "from_address": "sender@example.com",
        "subject": "Purchase Order PO-2024-0047",
        "body": "Please find attached our purchase order.",
        "attachments": [
            AttachmentPayload(
                filename="po.csv",
                content_type="text/csv",
                data="aXRlbSxxdHkscHJpY2UKV2lkZ2V0LDEwLDI1LjAw",  # base64 CSV
            )
        ],
        "received_at": "2024-11-15T10:30:00Z",
    }
    base.update(overrides)
    return WebhookEmailPayload(**base)


def _mock_extraction():
    """Create a fresh mock extraction for each test."""
    ext = MagicMock()
    ext.po_number = "PO-2024-0047"
    ext.po_date = "2024-11-15"
    ext.vendor.name = "Acme Corp"
    ext.vendor.contact = "acme@example.com"
    ext.requester = None
    ext.line_items = []
    ext.total_amount = 250.00
    ext.currency = "USD"
    ext.delivery_date = "2024-12-01"
    ext.payment_terms = "NET30"
    return ext


def _empty_result():
    from schemas.validation import ValidationCheckResult

    return ValidationCheckResult(check_type="VENDOR", result="PASS", details={}, tags=[])


class TestPipelineEmailWiring:
    @patch("services.pipeline.email_service")
    @patch("services.pipeline.classify_email", new_callable=AsyncMock)
    @patch("services.pipeline.extract_po_data", new_callable=AsyncMock)
    @patch("services.pipeline.validate_vendor", new_callable=AsyncMock)
    @patch("services.pipeline.validate_prices", new_callable=AsyncMock)
    @patch("services.pipeline.validate_policy", new_callable=AsyncMock)
    @patch("services.pipeline.validate_completeness", new_callable=AsyncMock)
    async def test_pipeline_records_inbound_email(
        self,
        mock_completeness,
        mock_policy,
        mock_prices,
        mock_vendor,
        mock_extract,
        mock_classify,
        mock_email_svc,
    ):
        """Verify pipeline creates an inbound EmailLog. Uses mock session."""
        from models import EmailLog

        mock_classify.return_value = True
        mock_extract.return_value = _mock_extraction()
        mock_vendor.return_value = _empty_result()
        mock_prices.return_value = _empty_result()
        mock_policy.return_value = _empty_result()
        mock_completeness.return_value = _empty_result()
        mock_email_svc.send_confirmation = AsyncMock()

        session = AsyncMock()

        from services.pipeline import process_email

        await process_email(_make_payload(), session)

        # Check session.add was called with an EmailLog (INBOUND)
        added_objects = [call.args[0] for call in session.add.call_args_list]
        inbound_emails = [
            obj for obj in added_objects if isinstance(obj, EmailLog) and obj.direction == "INBOUND"
        ]
        assert len(inbound_emails) == 1
        assert inbound_emails[0].email_type == "PO_SUBMISSION"
        assert inbound_emails[0].sender == "sender@example.com"

    @patch("services.pipeline.email_service")
    @patch("services.pipeline.classify_email", new_callable=AsyncMock)
    @patch("services.pipeline.extract_po_data", new_callable=AsyncMock)
    @patch("services.pipeline.validate_vendor", new_callable=AsyncMock)
    @patch("services.pipeline.validate_prices", new_callable=AsyncMock)
    @patch("services.pipeline.validate_policy", new_callable=AsyncMock)
    @patch("services.pipeline.validate_completeness", new_callable=AsyncMock)
    async def test_pipeline_sends_confirmation_on_approval(
        self,
        mock_completeness,
        mock_policy,
        mock_prices,
        mock_vendor,
        mock_extract,
        mock_classify,
        mock_email_svc,
        db_session,
    ):
        mock_classify.return_value = True
        mock_extract.return_value = _mock_extraction()
        mock_vendor.return_value = _empty_result()
        mock_prices.return_value = _empty_result()
        mock_policy.return_value = _empty_result()
        mock_completeness.return_value = _empty_result()
        mock_email_svc.send_confirmation = AsyncMock()

        from services.pipeline import process_email

        async with db_session.begin_nested():
            await process_email(_make_payload(), db_session)

        mock_email_svc.send_confirmation.assert_called_once()

    @patch("services.pipeline.email_service")
    @patch("services.pipeline.classify_email", new_callable=AsyncMock)
    @patch("services.pipeline.extract_po_data", new_callable=AsyncMock)
    @patch("services.pipeline.validate_vendor", new_callable=AsyncMock)
    @patch("services.pipeline.validate_prices", new_callable=AsyncMock)
    @patch("services.pipeline.validate_policy", new_callable=AsyncMock)
    @patch("services.pipeline.validate_completeness", new_callable=AsyncMock)
    async def test_pipeline_sends_ack_on_flagged(
        self,
        mock_completeness,
        mock_policy,
        mock_prices,
        mock_vendor,
        mock_extract,
        mock_classify,
        mock_email_svc,
        db_session,
    ):
        from schemas.validation import IssueTagResult, ValidationCheckResult

        mock_classify.return_value = True
        mock_extract.return_value = _mock_extraction()

        tagged_result = ValidationCheckResult(
            check_type="PRICE",
            result="WARNING",
            details={},
            tags=[IssueTagResult(tag="PRICE_MISMATCH", severity="SOFT", description="10% over")],
        )
        mock_vendor.return_value = _empty_result()
        mock_prices.return_value = tagged_result
        mock_policy.return_value = _empty_result()
        mock_completeness.return_value = _empty_result()
        mock_email_svc.send_acknowledgment = AsyncMock()

        from services.pipeline import process_email

        async with db_session.begin_nested():
            await process_email(_make_payload(), db_session)

        mock_email_svc.send_acknowledgment.assert_called_once()
