"""True end-to-end test: send PO email → poll → pipeline → response email.

Sends a sample PO to yourself via Gmail, then polls for it, runs the full
pipeline (classify → extract → validate → RAG → route), persists results,
and sends the appropriate response email back.

Usage:
    cd src/backend && uv run python -m scripts.test_e2e_email
    cd src/backend && uv run python -m scripts.test_e2e_email --po clean
    cd src/backend && uv run python -m scripts.test_e2e_email --po fuzzy
    cd src/backend && uv run python -m scripts.test_e2e_email --po bad
    cd src/backend && uv run python -m scripts.test_e2e_email --po all
"""

import argparse
import asyncio
import base64
import sys
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from sqlmodel import select

from core.config import settings
from core.database import async_session_factory
from core.observability import setup_logging
from models import (
    EmailLog,
    IssueTag,
    OrderStatus,
    ProcessingLog,
    PurchaseOrder,
    ValidationCheck,
)
from services.email import email_service
from services.knowledge import knowledge_service

SAMPLES_DIR = Path(__file__).resolve().parents[3] / "samples"

SAMPLE_POS = {
    # PDF samples
    "clean-pdf": {
        "file": "po_clean.pdf",
        "subject": "Purchase Order PO-2025-0147 — PLCs and Safety Components",
        "body": "Please find attached our purchase order for PLCs and safety components from Nordic Supply.",
        "expected": "APPROVED",
    },
    "fuzzy-pdf": {
        "file": "po_fuzzy.pdf",
        "subject": "Purchase Order PO-2025-0203 — Motors and Seals",
        "body": "Attached is the PO for AC motors and seal kits from Balkan Electr.",
        "expected": "APPROVED",
    },
    "bad-pdf": {
        "file": "po_bad.pdf",
        "subject": "Urgent: Office Furniture Order",
        "body": "Urgent order for ergonomic chairs and standing desks. PO attached.",
        "expected": "REJECTED",
    },
    # XLSX samples
    "clean-xlsx": {
        "file": "po_clean.xlsx",
        "subject": "Purchase Order PO-2025-0155 — Fasteners and Cable Trays",
        "body": "Please process the attached purchase order for fasteners from EuroFasteners GmbH.",
        "expected": "APPROVED",
    },
    "fuzzy-xlsx": {
        "file": "po_fuzzy.xlsx",
        "subject": "Purchase Order PO-2025-0210 — Busbars and Thermal Paste",
        "body": "Attached is our PO for copper busbars from S.Z. Metals.",
        "expected": "APPROVED",
    },
    "bad-xlsx": {
        "file": "po_bad.xlsx",
        "subject": "Urgent: Server Equipment Order",
        "body": "Please process this order for server racks and UPS systems urgently.",
        "expected": "REJECTED",
    },
    # Image samples
    "clean-img": {
        "file": "po_clean.png",
        "subject": "Purchase Order PO-2025-0162 — Lubricants and Seals",
        "body": "Attached is our purchase order for industrial lubricant and seal kits from Plovdiv Industrial.",
        "expected": "APPROVED",
    },
    "fuzzy-img": {
        "file": "po_fuzzy.png",
        "subject": "Purchase Order PO-2025-0218 — Safety Light Curtains",
        "body": "Please find attached the PO for safety light curtains from Dutch Logist.",
        "expected": "APPROVED",
    },
    "bad-img": {
        "file": "po_bad.png",
        "subject": "Purchase Order — CNC Parts from MediterraneanParts",
        "body": "Attached is a purchase order for custom machined parts. Please process.",
        "expected": "REJECTED",
    },
}


async def send_po_email(sample_key: str) -> str:
    """Send a sample PO as a Gmail message. Returns the message ID."""
    meta = SAMPLE_POS[sample_key]
    pdf_path = SAMPLES_DIR / meta["file"]

    # Add timestamp to subject to avoid matching old emails
    timestamp = int(time.time())
    subject = f"[E2E-{timestamp}] {meta['subject']}"

    msg = MIMEMultipart()
    msg["to"] = settings.agent_email
    msg["from"] = settings.agent_email
    msg["subject"] = subject

    msg.attach(MIMEText(meta["body"]))

    pdf_data = pdf_path.read_bytes()
    attachment = MIMEApplication(pdf_data, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=meta["file"])
    msg.attach(attachment)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = await asyncio.to_thread(
        email_service._service.users().messages().send(userId="me", body={"raw": raw}).execute
    )
    print(f"  Sent email: {subject}")
    print(f"  Message ID: {result['id']}")
    return subject


async def wait_for_email(subject_prefix: str, timeout: int = 30) -> bool:
    """Wait until the sent email appears as unread in the inbox."""
    print(f"  Waiting for email to arrive (up to {timeout}s)...")
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        results = await asyncio.to_thread(
            email_service._service.users()
            .messages()
            .list(userId="me", q=f"is:unread subject:{subject_prefix}")
            .execute
        )
        if results.get("messages"):
            print(f"  Email arrived after {time.monotonic() - start:.1f}s")
            return True
        await asyncio.sleep(2)
    print(f"  WARNING: Email not found after {timeout}s")
    return False


async def run_poll_cycle(subject_filter: str) -> int:
    """Fetch only the email matching our test subject and process it."""
    import asyncio

    from core.time import utc_now
    from schemas.webhook import AttachmentPayload, WebhookEmailPayload
    from services.pipeline import process_email

    svc = email_service._service

    # Search only for our specific test email
    results = await asyncio.to_thread(
        svc.users().messages().list(userId="me", q=f'is:unread subject:"{subject_filter}"').execute
    )
    messages = results.get("messages", [])
    if not messages:
        print(f"  No unread emails matching '{subject_filter}'")
        return 0

    processed = 0
    for msg_ref in messages:
        msg = await asyncio.to_thread(
            svc.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute
        )
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        from_addr = headers.get("from", "")
        subject = headers.get("subject", "")
        body = msg.get("snippet", "")

        attachments = []
        for part in msg["payload"].get("parts", []):
            if part.get("filename") and part.get("body", {}).get("attachmentId"):
                att = await asyncio.to_thread(
                    svc.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=msg_ref["id"], id=part["body"]["attachmentId"])
                    .execute
                )
                attachments.append(
                    AttachmentPayload(
                        filename=part["filename"],
                        content_type=part.get("mimeType", "application/octet-stream"),
                        data=att["data"],
                    )
                )

        if attachments:
            payload = WebhookEmailPayload(
                from_address=from_addr,
                subject=subject,
                body=body,
                attachments=attachments,
                received_at=utc_now().isoformat(),
            )
            async with async_session_factory() as session:
                await process_email(payload, session)
                processed += 1

        # Mark as read
        await asyncio.to_thread(
            svc.users()
            .messages()
            .modify(userId="me", id=msg_ref["id"], body={"removeLabelIds": ["UNREAD"]})
            .execute
        )

    return processed


async def print_results(tracking_id) -> None:
    """Fetch and display pipeline results from the database."""
    async with async_session_factory() as session:
        order = await session.get(PurchaseOrder, tracking_id)
        if not order:
            print("  ERROR: Order not found in database")
            return

        print("\n  --- Extraction ---")
        print(f"  PO Number:    {order.po_number or '(missing)'}")
        print(f"  Vendor:       {order.vendor_name or '(missing)'}")
        print(
            f"  Requester:    {order.requester_name or '(missing)'} / {order.requester_department or '(missing)'}"
        )
        print(f"  Total:        {order.total_amount} {order.currency}")
        print(f"  Delivery:     {order.delivery_date or '(missing)'}")
        print(f"  Terms:        {order.payment_terms or '(missing)'}")
        if order.line_items:
            items = order.line_items.get("items", [])
            print(f"  Line Items:   {len(items)}")
            for item in items:
                sku = item.get("sku") or "(no SKU)"
                desc = item.get("description", "")[:40]
                qty = item.get("quantity", "?")
                price = item.get("unit_price", "?")
                print(f"    - {sku}: {desc}  qty={qty}  price={price}")

        # Validation checks
        result = await session.exec(
            select(ValidationCheck).where(ValidationCheck.order_id == tracking_id)
        )
        checks = result.all()
        print("\n  --- Validation Checks ---")
        for check in checks:
            print(f"  [{check.check_type:>12}]  result={check.result}")

        # Issue tags
        result = await session.exec(select(IssueTag).where(IssueTag.order_id == tracking_id))
        tags = result.all()
        print(f"\n  --- Issue Tags ({len(tags)}) ---")
        for tag in tags:
            print(f"  [{tag.severity:>4}]  {tag.tag}: {tag.description or ''}")

        # Processing timeline
        result = await session.exec(
            select(ProcessingLog).where(ProcessingLog.order_id == tracking_id)
        )
        logs = result.all()
        total_ms = sum(entry.duration_ms or 0 for entry in logs)
        print(f"\n  --- Processing Timeline (total: {total_ms}ms) ---")
        for entry in sorted(logs, key=lambda e: e.created_at):
            ms = f"{entry.duration_ms}ms" if entry.duration_ms else "?"
            print(f"  {entry.step:<20} {entry.status:<10} {ms:>8}")

        # Emails sent
        result = await session.exec(select(EmailLog).where(EmailLog.order_id == tracking_id))
        emails = result.all()
        print("\n  --- Emails ---")
        for email in emails:
            print(
                f"  [{email.direction:>8}]  {email.email_type:<16}  {email.recipient or email.sender}"
            )

        # Final status
        status = order.status
        status_label = {
            OrderStatus.APPROVED.value: "AUTO-APPROVED",
            OrderStatus.PENDING_REVIEW.value: "FLAGGED FOR REVIEW",
            OrderStatus.REJECTED.value: "REJECTED (pending human review)",
            OrderStatus.FAILED.value: "FAILED",
        }
        print(f"\n  >>> RESULT: {status_label.get(status, status)} <<<")
        return status


async def run_e2e(sample_key: str) -> bool:
    """Run full end-to-end test for a single sample PO."""
    meta = SAMPLE_POS[sample_key]
    print(f"\n{'=' * 70}")
    print(f"  E2E Test: {sample_key} ({meta['file']})")
    print(f"  Expected: {meta['expected']}")
    print(f"{'=' * 70}")

    # Step 1: Send email
    print("\n  Step 1: Sending PO email...")
    subject = await send_po_email(sample_key)

    # Step 2: Wait for it to appear
    print("\n  Step 2: Waiting for delivery...")
    # Extract the unique prefix for searching
    prefix = subject.split("]")[0].replace("[", "")
    arrived = await wait_for_email(prefix)
    if not arrived:
        print("  FAILED: Email never arrived")
        return False

    # Step 3: Poll and process (only our test email)
    print("\n  Step 3: Running pipeline (poll + classify + extract + validate + route)...")
    count = await run_poll_cycle(prefix)
    print(f"  Processed {count} email(s)")

    if count == 0:
        print("  FAILED: No emails processed")
        return False

    # Step 4: Show results — find the most recent order
    print("\n  Step 4: Results")
    async with async_session_factory() as session:
        result = await session.exec(
            select(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).limit(1)
        )
        order = result.first()
        if not order:
            print("  FAILED: No order found in database")
            return False

    status = await print_results(order.id)

    # Step 5: Verify expectation
    expected = meta["expected"]
    passed = status == expected
    print(f"\n  {'PASS' if passed else 'FAIL'}: expected={expected}, got={status}")
    return passed


async def main(po_keys: list[str]):
    setup_logging()

    print("Authenticating Gmail...")
    await email_service.authenticate()

    print("Initializing RAG knowledge base...")
    await knowledge_service.initialize()

    results = {}
    for key in po_keys:
        results[key] = await run_e2e(key)

    # Summary
    print(f"\n{'=' * 70}")
    print("  E2E Test Summary")
    print(f"{'=' * 70}")
    for key, passed in results.items():
        mark = "PASS" if passed else "FAIL"
        print(
            f"  [{mark}]  {key} ({SAMPLE_POS[key]['file']}) — expected {SAMPLE_POS[key]['expected']}"
        )

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  {passed}/{total} passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end email pipeline test")
    all_keys = list(SAMPLE_POS.keys())
    group_keys = {
        "all": all_keys,
        "pdf": [k for k in all_keys if k.endswith("-pdf")],
        "xlsx": [k for k in all_keys if k.endswith("-xlsx")],
        "img": [k for k in all_keys if k.endswith("-img")],
        "clean": [k for k in all_keys if k.startswith("clean")],
        "fuzzy": [k for k in all_keys if k.startswith("fuzzy")],
        "bad": [k for k in all_keys if k.startswith("bad")],
    }
    valid = list(group_keys.keys()) + all_keys
    parser.add_argument(
        "--po",
        type=str,
        default="clean-pdf",
        choices=valid,
        help="Sample key, group (pdf/xlsx/img/clean/fuzzy/bad), or 'all'",
    )
    args = parser.parse_args()

    keys = group_keys.get(args.po, [args.po])
    asyncio.run(main(keys))
