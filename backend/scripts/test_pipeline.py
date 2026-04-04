"""End-to-end pipeline test with sample PO files (no email integration).

Reads sample PDFs from samples/, builds fake email payloads, and runs them
through the full pipeline: classify → extract → validate (DB) → RAG validate → route.

Usage:
    cd backend && uv run python -m scripts.test_pipeline
    cd backend && uv run python -m scripts.test_pipeline --file ../samples/po_clean.pdf
    cd backend && uv run python -m scripts.test_pipeline --skip-classify
"""

import argparse
import asyncio
import base64
import sys
from pathlib import Path

from loguru import logger
from sqlmodel import select

from core.database import async_session_factory
from core.observability import setup_logging
from models import (
    IssueTag,
    OrderStatus,
    ProcessingLog,
    PurchaseOrder,
    ValidationCheck,
)
from services.knowledge import knowledge_service

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"

# Sample PO metadata for building fake email payloads
SAMPLE_POS = {
    "po_clean.pdf": {
        "from": "ivan.petrov@company.bg",
        "subject": "Purchase Order PO-2024-0047",
        "body": "Please find attached our purchase order for sensor modules.",
    },
    "po_fuzzy.pdf": {
        "from": "maria.ivanova@company.bg",
        "subject": "Purchase Order PO-2024-0088",
        "body": "Attached is the PO for timing belts from Acme Corp.",
    },
    "po_bad.pdf": {
        "from": "georgi.dimitrov@company.bg",
        "subject": "Urgent: Purchase Order for Controllers",
        "body": "Urgent order - expedited shipping required. PO attached.",
    },
}


def build_payload(pdf_path: Path) -> dict:
    """Build a webhook-style payload from a PDF file."""
    pdf_data = pdf_path.read_bytes()
    meta = SAMPLE_POS.get(pdf_path.name, {})

    return {
        "from": meta.get("from", "test@example.com"),
        "subject": meta.get("subject", f"Purchase Order - {pdf_path.stem}"),
        "body": meta.get("body", "Please find the attached purchase order."),
        "attachments": [
            {
                "filename": pdf_path.name,
                "content_type": "application/pdf",
                "data": base64.b64encode(pdf_data).decode(),
            }
        ],
        "received_at": "2024-11-15T10:30:00Z",
    }


async def run_pipeline(pdf_path: Path, skip_classify: bool = False) -> None:
    """Run the full pipeline for a single PDF and print results."""
    from schemas.webhook import WebhookEmailPayload
    from services.pipeline import process_email

    print(f"\n{'='*70}")
    print(f"  Processing: {pdf_path.name}")
    print(f"{'='*70}")

    payload_dict = build_payload(pdf_path)
    payload = WebhookEmailPayload(**payload_dict)

    if skip_classify:
        # Patch classifier to always return True
        import agent.classifier as clf

        original = clf.classify_email

        async def always_po(*_args, **_kwargs):
            return True

        clf.classify_email = always_po

    async with async_session_factory() as session:
        try:
            tracking_id = await process_email(payload, session)
        except Exception:
            logger.exception("Pipeline failed for {}", pdf_path.name)
            return
        finally:
            if skip_classify:
                clf.classify_email = original

    # Fetch results from DB
    await print_results(tracking_id)


async def print_results(tracking_id) -> None:
    """Fetch and display pipeline results from the database."""
    async with async_session_factory() as session:
        # Fetch order
        order = await session.get(PurchaseOrder, tracking_id)
        if not order:
            print("  ERROR: Order not found in database")
            return

        print("\n  --- Extraction ---")
        print(f"  PO Number:    {order.po_number or '(missing)'}")
        print(f"  Vendor:       {order.vendor_name or '(missing)'}")
        print(f"  Requester:    {order.requester_name or '(missing)'} / {order.requester_department or '(missing)'}")
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

        # Fetch validation checks
        stmt = select(ValidationCheck).where(ValidationCheck.order_id == tracking_id)
        result = await session.exec(stmt)
        checks = result.all()

        print("\n  --- Validation Checks ---")
        for check in checks:
            print(f"  [{check.check_type:>12}]  result={check.result}")
            if check.check_type == "RAG" and check.details:
                rag = check.details
                if "adjustments" in rag:
                    for adj in rag["adjustments"]:
                        action = adj.get("action", "?")
                        tag = adj.get("original_tag", "?")
                        reason = adj.get("reasoning", "")[:80]
                        severity = adj.get("adjusted_severity", "")
                        sev_str = f" -> {severity}" if severity else ""
                        print(f"               {action:>10} {tag}{sev_str}: {reason}")
                if "new_tags" in rag:
                    for nt in rag["new_tags"]:
                        print(f"               {'NEW':>10} {nt.get('tag')}/{nt.get('severity')}: {nt.get('description', '')[:60]}")
                if "summary" in rag:
                    print(f"               Summary: {rag['summary'][:100]}")

        # Fetch issue tags
        stmt = select(IssueTag).where(IssueTag.order_id == tracking_id)
        result = await session.exec(stmt)
        tags = result.all()

        print(f"\n  --- Final Issue Tags ({len(tags)}) ---")
        for tag in tags:
            print(f"  [{tag.severity:>4}]  {tag.tag}: {tag.description or ''}")

        # Fetch processing logs
        stmt = select(ProcessingLog).where(ProcessingLog.order_id == tracking_id)
        result = await session.exec(stmt)
        logs = result.all()

        print("\n  --- Processing Timeline ---")
        for log_entry in sorted(logs, key=lambda entry: entry.created_at):
            ms = f"{log_entry.duration_ms}ms" if log_entry.duration_ms else "?"
            print(f"  {log_entry.step:<20} {log_entry.status:<10} {ms:>8}")

        # Final status
        status = order.status
        status_emoji = {
            OrderStatus.APPROVED.value: "[APPROVED]",
            OrderStatus.PENDING_REVIEW.value: "[PENDING REVIEW]",
            OrderStatus.REJECTED.value: "[REJECTED]",
            OrderStatus.FAILED.value: "[FAILED]",
        }
        print(f"\n  >>> ROUTING DECISION: {status_emoji.get(status, status)} <<<")


async def main(files: list[Path], skip_classify: bool) -> None:
    setup_logging()

    # Initialize knowledge service (connect to existing LanceDB)
    await knowledge_service.initialize()

    for pdf_path in files:
        await run_pipeline(pdf_path, skip_classify=skip_classify)

    print(f"\n{'='*70}")
    print(f"  Done — processed {len(files)} PO(s)")
    print(f"{'='*70}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test pipeline with sample PO files")
    parser.add_argument(
        "--file",
        type=str,
        help="Path to a specific PDF to test (default: all samples)",
    )
    parser.add_argument(
        "--skip-classify",
        action="store_true",
        help="Skip email classification (assume all files are POs)",
    )
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: File not found: {path}")
            sys.exit(1)
        files = [path]
    else:
        files = sorted(SAMPLES_DIR.glob("*.pdf"))
        if not files:
            print(f"ERROR: No PDF files found in {SAMPLES_DIR}")
            sys.exit(1)

    asyncio.run(main(files, skip_classify=args.skip_classify))
