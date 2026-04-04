import base64
import time
import uuid
from datetime import datetime

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from agent.classifier import classify_email
from agent.extractor import extract_po_data
from agent.router import route_order
from agent.validator import (
    validate_completeness,
    validate_policy,
    validate_prices,
    validate_vendor,
)
from core.config import settings
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
)
from schemas.webhook import WebhookEmailPayload
from services.email import email_service
from services.files import (
    detect_file_type,
    extract_images_from_pdf,
    extract_text_from_csv,
    extract_text_from_pdf,
)


async def process_email(payload: WebhookEmailPayload, session: AsyncSession) -> uuid.UUID:
    """Full pipeline: classify -> extract -> validate -> route -> persist."""
    tracking_id = uuid.uuid4()
    log = logger.bind(correlation_id=str(tracking_id))

    try:
        # Step 1: Classification
        step_start = time.monotonic()
        log.bind(step="classification").info("Classifying email")
        is_po = await classify_email(
            subject=payload.subject,
            body=payload.body,
            filenames=[a.filename for a in payload.attachments],
        )
        await _log_step(session, tracking_id, "classification", step_start, {"is_po": is_po})

        if not is_po:
            log.info("Email classified as non-PO, skipping")
            return tracking_id

        # Step 2: File processing
        step_start = time.monotonic()
        attachment = payload.attachments[0]
        file_data = base64.b64decode(attachment.data)
        file_type = detect_file_type(attachment.filename, attachment.content_type, file_data)

        content = None
        images = None
        if file_type == "csv":
            content = await extract_text_from_csv(file_data)
        elif file_type == "pdf_scanned":
            images = await extract_images_from_pdf(file_data)
        else:  # pdf_digital or image
            if file_type == "image":
                images = [file_data]
            else:
                content = await extract_text_from_pdf(file_data)
        await _log_step(
            session, tracking_id, "file_processing", step_start, {"file_type": file_type}
        )

        # Step 3: Extraction
        step_start = time.monotonic()
        extraction = await extract_po_data(content=content, images=images)
        await _log_step(session, tracking_id, "extraction", step_start)

        # Step 4: Validation
        step_start = time.monotonic()
        validation_results = [
            await validate_vendor(extraction),
            await validate_prices(extraction),
            await validate_policy(extraction),
            await validate_completeness(extraction),
        ]
        all_tags = []
        for vr in validation_results:
            all_tags.extend(vr.tags)
        await _log_step(
            session, tracking_id, "validation", step_start, {"tag_count": len(all_tags)}
        )

        # Step 5: Routing
        step_start = time.monotonic()
        status = route_order(all_tags)
        await _log_step(session, tracking_id, "routing", step_start, {"status": status.value})

        # Step 6: Persist
        order = PurchaseOrder(
            id=tracking_id,
            po_number=extraction.po_number,
            po_date=extraction.po_date,
            vendor_name=extraction.vendor.name,
            vendor_contact=extraction.vendor.contact,
            requester_name=extraction.requester.name if extraction.requester else None,
            requester_department=extraction.requester.department if extraction.requester else None,
            line_items={"items": [item.model_dump() for item in extraction.line_items]},
            total_amount=extraction.total_amount,
            currency=extraction.currency,
            delivery_date=extraction.delivery_date,
            payment_terms=extraction.payment_terms,
            status=status.value,
            original_filename=attachment.filename,
            sender_email=payload.from_address,
        )
        session.add(order)
        await session.flush()

        for vr in validation_results:
            check = ValidationCheck(
                order_id=tracking_id,
                check_type=vr.check_type.value,
                result=vr.result.value,
                details=vr.details,
            )
            session.add(check)

        for tag_result in all_tags:
            tag = IssueTag(
                order_id=tracking_id,
                tag=tag_result.tag.value,
                severity=tag_result.severity.value,
                description=tag_result.description,
            )
            session.add(tag)

        # Record inbound email
        inbound_email = EmailLog(
            order_id=tracking_id,
            direction=EmailDirection.INBOUND.value,
            email_type=EmailType.PO_SUBMISSION.value,
            sender=payload.from_address,
            recipient=settings.agent_email,
            subject=payload.subject,
            sent_at=datetime.fromisoformat(payload.received_at.replace("Z", "+00:00")).replace(
                tzinfo=None
            ),
        )
        session.add(inbound_email)

        await session.commit()

        # Step 7: Send email response (best-effort)
        try:
            if status == OrderStatus.APPROVED:
                await email_service.send_confirmation(order, session)
            else:
                await email_service.send_acknowledgment(order, session)
            await session.commit()
        except Exception:
            log.warning("Failed to send email response — continuing")

        log.info("Pipeline complete — status={}", status.value)
        return tracking_id

    except Exception:
        log.exception("Pipeline failed")
        order = PurchaseOrder(id=tracking_id, status=OrderStatus.FAILED.value)
        session.add(order)
        await session.commit()
        raise


async def _log_step(
    session: AsyncSession,
    order_id: uuid.UUID,
    step: str,
    start_time: float,
    metadata: dict | None = None,
) -> None:
    duration_ms = int((time.monotonic() - start_time) * 1000)
    log_entry = ProcessingLog(
        order_id=order_id,
        step=step,
        status=ProcessingStepStatus.COMPLETED.value,
        duration_ms=duration_ms,
        metadata_=metadata,
    )
    session.add(log_entry)
