import base64
import time
import uuid
from datetime import datetime

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from agent.classifier import classify_email
from agent.extractor import extract_po_data
from agent.rag_validator import apply_rag_adjustments, rag_validate
from agent.router import route_order
from agent.validator import (
    validate_completeness,
    validate_policy,
    validate_prices,
    validate_vendor,
)
from core.config import settings
from core.time import utc_now
from models import (
    EmailDirection,
    EmailLog,
    EmailType,
    IssueTag,
    OrderStatus,
    ProcessingLog,
    ProcessingStepStatus,
    PurchaseOrder,
    ValidationCheck,
    ValidationCheckType,
)
from schemas.webhook import AttachmentPayload, WebhookEmailPayload
from services.email import email_service
from services.files import (
    detect_file_type,
    extract_images_from_pdf,
    extract_text_from_csv,
    extract_text_from_pdf,
    extract_text_from_xlsx,
)


async def create_placeholder_orders(
    payload: WebhookEmailPayload,
    session: AsyncSession,
) -> tuple[uuid.UUID, list[uuid.UUID]]:
    """Create one PROCESSING placeholder per attachment so the UI can display them
    immediately. Returns (batch_id, placeholder_ids).

    Caller is responsible for committing the session.
    """
    batch_id = uuid.uuid4()
    placeholder_ids: list[uuid.UUID] = []

    for attachment in payload.attachments:
        order_id = uuid.uuid4()
        session.add(
            PurchaseOrder(
                id=order_id,
                status=OrderStatus.PROCESSING.value,
                original_filename=attachment.filename,
                sender_email=payload.from_address,
                batch_id=batch_id,
            )
        )
        placeholder_ids.append(order_id)

    return batch_id, placeholder_ids


async def process_placeholders(
    payload: WebhookEmailPayload,
    batch_id: uuid.UUID,
    placeholder_ids: list[uuid.UUID],
    session: AsyncSession,
) -> None:
    """Run the full pipeline against pre-created placeholder orders:
    classify -> process each attachment -> send summary email.

    If classification says the email is not a PO, all placeholders are deleted.
    """
    log = logger.bind(batch_id=str(batch_id))

    # Step 1: Classification (once per email)
    step_start = time.monotonic()
    log.bind(step="classification").info("Classifying email")
    is_po = await classify_email(
        subject=payload.subject,
        body=payload.body,
        filenames=[a.filename for a in payload.attachments],
    )

    if not is_po:
        log.info("Email classified as non-PO — removing placeholders")
        for order_id in placeholder_ids:
            order = await session.get(PurchaseOrder, order_id)
            if order is not None:
                await session.delete(order)
        await session.commit()
        return

    classify_duration_ms = int((time.monotonic() - step_start) * 1000)

    # Step 2: Process each attachment, updating its placeholder
    orders: list[PurchaseOrder] = []
    for attachment, order_id in zip(payload.attachments, placeholder_ids, strict=True):
        try:
            order = await _process_attachment(
                attachment=attachment,
                payload=payload,
                order_id=order_id,
                batch_id=batch_id,
                classify_duration_ms=classify_duration_ms,
                session=session,
            )
            orders.append(order)
        except Exception:
            log.exception("Failed to process attachment {}", attachment.filename)

    if not orders:
        log.warning("No attachments processed successfully")
        await session.commit()
        return

    await session.commit()

    # Step 3: Send one summary email for all POs in this batch
    try:
        await email_service.send_batch_summary(orders, session)
        await session.commit()
    except Exception:
        log.warning("Failed to send batch summary email — continuing")

    log.info(
        "Batch complete — {} PO(s): {}",
        len(orders),
        ", ".join(f"{o.po_number or o.original_filename}={o.status}" for o in orders),
    )


async def process_email(payload: WebhookEmailPayload, session: AsyncSession) -> uuid.UUID:
    """Convenience one-shot: create placeholders and process them in the same
    session. Does not commit between phases — used by tests and by the Gmail
    poller (which opens a dedicated session per email).
    """
    batch_id, placeholder_ids = await create_placeholder_orders(payload, session)
    await process_placeholders(payload, batch_id, placeholder_ids, session)
    return batch_id


async def _process_attachment(
    attachment: AttachmentPayload,
    payload: WebhookEmailPayload,
    order_id: uuid.UUID,
    batch_id: uuid.UUID,
    classify_duration_ms: int,
    session: AsyncSession,
) -> PurchaseOrder:
    """Process a single attachment through extract -> validate -> RAG -> route and
    update its pre-created placeholder PurchaseOrder in place.
    """
    log = logger.bind(correlation_id=str(order_id), batch_id=str(batch_id))
    pending_logs: list[dict] = []

    # Record classification step (shared across batch)
    pending_logs.append({
        "order_id": order_id,
        "step": "classification",
        "status": ProcessingStepStatus.COMPLETED.value,
        "duration_ms": classify_duration_ms,
        "metadata_": {"is_po": True},
    })

    order = await session.get(PurchaseOrder, order_id)
    if order is None:
        msg = f"Placeholder order {order_id} not found"
        raise RuntimeError(msg)

    try:
        # File processing
        step_start = time.monotonic()
        file_data = base64.urlsafe_b64decode(attachment.data + "==")
        file_type = detect_file_type(attachment.filename, attachment.content_type, file_data)

        content = None
        images = None
        if file_type == "csv":
            content = await extract_text_from_csv(file_data)
        elif file_type == "xlsx":
            content = await extract_text_from_xlsx(file_data)
        elif file_type == "pdf_scanned":
            images = await extract_images_from_pdf(file_data)
        elif file_type == "image":
            images = [file_data]
        else:
            content = await extract_text_from_pdf(file_data)
        pending_logs.append(
            _make_log(order_id, "file_processing", step_start, {"file_type": file_type})
        )

        # Extraction
        step_start = time.monotonic()
        extraction = await extract_po_data(content=content, images=images)
        pending_logs.append(_make_log(order_id, "extraction", step_start))

        # Deterministic validation
        step_start = time.monotonic()
        validation_results = [
            await validate_vendor(extraction, session),
            await validate_prices(extraction, session),
            await validate_policy(extraction, session),
            await validate_completeness(extraction),
        ]
        all_tags = []
        for vr in validation_results:
            all_tags.extend(vr.tags)
        pending_logs.append(
            _make_log(order_id, "validation", step_start, {"tag_count": len(all_tags)})
        )

        # RAG validation
        step_start = time.monotonic()
        all_details = {vr.check_type.value: vr.details for vr in validation_results}
        rag_result = await rag_validate(extraction, all_tags, all_details)
        final_tags = apply_rag_adjustments(all_tags, rag_result)
        pending_logs.append(
            _make_log(
                order_id,
                "rag_validation",
                step_start,
                {
                    "adjustments": len(rag_result.adjustments),
                    "new_tags": len(rag_result.new_tags),
                    "tags_before": len(all_tags),
                    "tags_after": len(final_tags),
                },
            )
        )

        # Routing
        step_start = time.monotonic()
        status = route_order(final_tags)
        pending_logs.append(
            _make_log(order_id, "routing", step_start, {"status": status.value})
        )

        # Update placeholder with extracted data + final status
        order.po_number = extraction.po_number
        order.po_date = extraction.po_date
        order.vendor_name = extraction.vendor.name
        order.vendor_contact = extraction.vendor.contact
        order.requester_name = extraction.requester.name if extraction.requester else None
        order.requester_department = (
            extraction.requester.department if extraction.requester else None
        )
        order.line_items = {"items": [item.model_dump() for item in extraction.line_items]}
        order.total_amount = extraction.total_amount
        order.currency = extraction.currency
        order.delivery_date = extraction.delivery_date
        order.payment_terms = extraction.payment_terms
        order.status = status.value
        order.updated_at = utc_now()
        session.add(order)
        await session.flush()

        # Persist children
        for vr in validation_results:
            session.add(
                ValidationCheck(
                    order_id=order_id,
                    check_type=vr.check_type.value,
                    result=vr.result.value,
                    details=vr.details,
                )
            )

        session.add(
            ValidationCheck(
                order_id=order_id,
                check_type=ValidationCheckType.RAG.value,
                result="PASS" if not final_tags else "WARNING",
                details=rag_result.model_dump(),
            )
        )

        for tag_result in final_tags:
            session.add(
                IssueTag(
                    order_id=order_id,
                    tag=tag_result.tag.value,
                    severity=tag_result.severity.value,
                    description=tag_result.description,
                )
            )

        for log_data in pending_logs:
            session.add(ProcessingLog(**log_data))

        # Record inbound email
        session.add(
            EmailLog(
                order_id=order_id,
                direction=EmailDirection.INBOUND.value,
                email_type=EmailType.PO_SUBMISSION.value,
                sender=payload.from_address,
                recipient=settings.agent_email,
                subject=payload.subject,
                sent_at=datetime.fromisoformat(
                    payload.received_at.replace("Z", "+00:00")
                ),
            )
        )

        log.info("Attachment {} — status={}", attachment.filename, status.value)
        return order

    except Exception:
        log.exception("Pipeline failed for {}", attachment.filename)
        order.status = OrderStatus.FAILED.value
        order.updated_at = utc_now()
        session.add(order)
        await session.flush()
        raise


def _make_log(
    order_id: uuid.UUID,
    step: str,
    start_time: float,
    metadata: dict | None = None,
) -> dict:
    """Build a processing log dict (inserted after order is created)."""
    return {
        "order_id": order_id,
        "step": step,
        "status": ProcessingStepStatus.COMPLETED.value,
        "duration_ms": int((time.monotonic() - start_time) * 1000),
        "metadata_": metadata,
    }
