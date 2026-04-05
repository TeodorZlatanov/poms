import asyncio
import base64
import uuid
from email.mime.text import MIMEText
from pathlib import Path

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import settings
from core.time import utc_now
from models import (
    EmailDirection,
    EmailLog,
    EmailType,
    IssueTag,
    OrderStatus,
    PurchaseOrder,
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

STATUS_LABELS = {
    OrderStatus.APPROVED.value: "Approved",
    OrderStatus.PENDING_REVIEW.value: "Under Review",
    OrderStatus.REJECTED.value: "Under Review",
}

TAG_DESCRIPTIONS = {
    "UNKNOWN_VENDOR": "The vendor is not registered in our approved vendor list",
    "EXPIRED_CONTRACT": "The vendor's contract has expired",
    "VENDOR_FUZZY_MATCH": "The vendor name doesn't exactly match our records",
    "PRICE_MISMATCH": "One or more item prices differ significantly from our catalog",
    "OVER_LIMIT": "The order total exceeds the department's spending limit",
    "TERMS_VIOLATION": "The payment terms are outside our allowed policy",
    "MISSING_FIELD": None,  # handled specially below
    "UNKNOWN_PRODUCT": "One or more items are not in our product catalog",
}

FIELD_LABELS = {
    "po_number": "PO number",
    "vendor.contact": "vendor contact email",
    "delivery_date": "delivery date",
    "total_amount": "total amount",
    "vendor.name": "vendor name",
}


def _po_label(order: PurchaseOrder) -> str:
    return order.po_number or order.original_filename or "N/A"


def _humanize_tag(tag: str, description: str | None) -> str:
    """Turn a technical tag + description into a human-readable sentence."""
    # For MISSING_FIELD, extract the field name and make it readable
    if tag == "MISSING_FIELD" and description:
        for field_key, label in FIELD_LABELS.items():
            if field_key in description:
                if "Required" in description:
                    return f"Required field missing: {label}"
                return f"Recommended field missing: {label}"
        if "sku" in (description or "").lower():
            return "Item SKU/part number is missing"
        return description.replace("Required field ", "").replace("Recommended field ", "")

    # For other tags, use the friendly description
    friendly = TAG_DESCRIPTIONS.get(tag)
    if friendly:
        return friendly

    # Fallback: format the tag name
    return tag.replace("_", " ").title()


class EmailService:
    def __init__(self) -> None:
        self._service = None
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    async def authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2 credentials."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds_path = Path(settings.gmail_credentials_path)
        token_path = Path(settings.gmail_token_path)

        if not creds_path.exists():
            msg = f"Gmail credentials file not found: {creds_path}"
            raise FileNotFoundError(msg)

        creds = None
        if token_path.exists():
            creds = await asyncio.to_thread(
                Credentials.from_authorized_user_file, str(token_path), SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                await asyncio.to_thread(creds.refresh, Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = await asyncio.to_thread(flow.run_local_server, port=0)
            token_path.write_text(creds.to_json())

        self._service = await asyncio.to_thread(build, "gmail", "v1", credentials=creds)
        self._authenticated = True
        logger.info("Gmail API authenticated successfully")

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        order_id: uuid.UUID | None = None,
        email_type: str = EmailType.CONFIRMATION.value,
        session: AsyncSession | None = None,
        thread_id: str | None = None,
    ) -> str | None:
        """Compose and send an email via Gmail API. Returns the Gmail message ID."""
        if not self._authenticated:
            logger.warning("Email service not authenticated — skipping send")
            return None

        message = MIMEText(body)
        message["to"] = to
        message["from"] = settings.agent_email
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        send_body: dict = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id

        result = await asyncio.to_thread(
            self._service.users().messages().send(userId="me", body=send_body).execute
        )
        gmail_msg_id = result.get("id")
        logger.info("Email sent to {} — subject: {}", to, subject)

        if session and order_id:
            email_log = EmailLog(
                order_id=order_id,
                direction=EmailDirection.OUTBOUND.value,
                email_type=email_type,
                sender=settings.agent_email,
                recipient=to,
                subject=subject,
                sent_at=utc_now(),
            )
            session.add(email_log)

        return gmail_msg_id

    async def send_batch_summary(
        self,
        orders: list[PurchaseOrder],
        session: AsyncSession,
    ) -> None:
        """Send a single summary email for all POs processed from one email."""
        if not orders:
            return

        sender = orders[0].sender_email
        if not sender:
            return

        log = logger.bind(batch_id=str(orders[0].batch_id))
        log.info("Sending batch summary to {} — {} PO(s)", sender, len(orders))

        # Build subject
        if len(orders) == 1:
            order = orders[0]
            status_label = STATUS_LABELS.get(order.status, order.status)
            subject = f"PO {_po_label(order)} — {status_label}"
        else:
            subject = f"Purchase Order Results — {len(orders)} PO(s) Processed"

        # Build body
        lines = ["Your purchase order(s) have been processed.\n"]

        for order in orders:
            status_label = STATUS_LABELS.get(order.status, order.status)
            lines.append(f"  {_po_label(order)}: {status_label}")
            lines.append(f"    Vendor: {order.vendor_name or 'N/A'}")
            lines.append(f"    Total: {order.total_amount or 'N/A'} {order.currency or ''}")
            lines.append("")

        # Summary counts
        approved = sum(1 for o in orders if o.status == OrderStatus.APPROVED.value)
        review = sum(
            1
            for o in orders
            if o.status in (OrderStatus.PENDING_REVIEW.value, OrderStatus.REJECTED.value)
        )

        if approved and not review:
            lines.append("All purchase orders have been approved. No action is required.")
        elif review:
            lines.append(
                f"{review} order(s) require review. "
                "You will be notified when a decision is made."
            )

        body = "\n".join(lines)
        email_type = (
            EmailType.CONFIRMATION.value if not review else EmailType.ACKNOWLEDGMENT.value
        )

        # Send once, log against all orders
        gmail_msg_id = await self.send_email(
            to=sender,
            subject=subject,
            body=body,
            order_id=orders[0].id,
            email_type=email_type,
            session=session,
        )

        # Store the Gmail thread ID on all orders for reply threading
        if gmail_msg_id:
            for order in orders:
                order.batch_email_message_id = gmail_msg_id
                session.add(order)

        # Log email against remaining orders too
        for order in orders[1:]:
            session.add(
                EmailLog(
                    order_id=order.id,
                    direction=EmailDirection.OUTBOUND.value,
                    email_type=email_type,
                    sender=settings.agent_email,
                    recipient=sender,
                    subject=subject,
                    sent_at=utc_now(),
                )
            )

    async def send_decision(
        self,
        order: PurchaseOrder,
        decision: str,
        comment: str | None,
        session: AsyncSession,
    ) -> None:
        """Send decision email after reviewer acts, threaded to the original batch email."""
        from sqlmodel import select

        log = logger.bind(correlation_id=str(order.id))
        log.info("Sending decision email to {} — decision={}", order.sender_email, decision)

        if decision == "approve":
            subject = f"PO {_po_label(order)} — Approved"
            body = (
                f"Your purchase order has been approved by a reviewer.\n\n"
                f"PO Number: {_po_label(order)}\n"
                f"Vendor: {order.vendor_name or 'N/A'}\n"
                f"Total: {order.total_amount or 'N/A'} {order.currency or ''}\n"
            )
            if comment:
                body += f"\nReviewer comment: {comment}\n"
            email_type = EmailType.CONFIRMATION.value
        else:
            subject = f"PO {_po_label(order)} — Rejected"
            body = (
                f"Your purchase order has been reviewed and could not be approved.\n\n"
                f"PO Number: {_po_label(order)}\n"
                f"Vendor: {order.vendor_name or 'N/A'}\n"
                f"Total: {order.total_amount or 'N/A'} {order.currency or ''}\n"
            )
            if comment:
                body += f"\nReviewer note: {comment}\n"

            result = await session.exec(select(IssueTag).where(IssueTag.order_id == order.id))
            tags = result.all()
            if tags:
                # Deduplicate similar messages (e.g. multiple missing SKUs)
                seen: set[str] = set()
                body += "\nThe following issues were found:\n"
                for t in tags:
                    line = _humanize_tag(t.tag, t.description)
                    if line not in seen:
                        seen.add(line)
                        body += f"  - {line}\n"

            body += (
                "\nPlease correct the issues listed above and resubmit your purchase order. "
                "If you have questions, contact the procurement team."
            )
            email_type = EmailType.REJECTION.value

        if order.sender_email:
            await self.send_email(
                to=order.sender_email,
                subject=subject,
                body=body,
                order_id=order.id,
                email_type=email_type,
                session=session,
                thread_id=order.batch_email_message_id,
            )

    async def fetch_new_emails(self) -> list:
        """Poll inbox for unread emails with attachments, mark as read."""
        from schemas.webhook import AttachmentPayload, WebhookEmailPayload

        if not self._authenticated:
            logger.warning("Email service not authenticated — skipping fetch")
            return []

        results = await asyncio.to_thread(
            self._service.users().messages().list(userId="me", q="is:unread has:attachment").execute
        )
        messages = results.get("messages", [])
        if not messages:
            return []

        payloads = []
        for msg_ref in messages:
            try:
                msg = await asyncio.to_thread(
                    self._service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="full")
                    .execute
                )
                headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
                from_addr = headers.get("from", "")
                subject = headers.get("subject", "")
                body = msg.get("snippet", "")

                attachments = []
                for part in msg["payload"].get("parts", []):
                    if part.get("filename") and part.get("body", {}).get("attachmentId"):
                        att = await asyncio.to_thread(
                            self._service.users()
                            .messages()
                            .attachments()
                            .get(
                                userId="me",
                                messageId=msg_ref["id"],
                                id=part["body"]["attachmentId"],
                            )
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
                    payloads.append(
                        WebhookEmailPayload(
                            from_address=from_addr,
                            subject=subject,
                            body=body,
                            attachments=attachments,
                            received_at=utc_now().isoformat(),
                        )
                    )

                # Mark as read
                await asyncio.to_thread(
                    self._service.users()
                    .messages()
                    .modify(userId="me", id=msg_ref["id"], body={"removeLabelIds": ["UNREAD"]})
                    .execute
                )
            except Exception:
                logger.exception("Failed to process Gmail message {}", msg_ref["id"])

        logger.info("Fetched {} new emails from Gmail", len(payloads))
        return payloads


email_service = EmailService()
