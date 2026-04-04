import asyncio
import base64
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from core.config import settings
from models import (
    EmailDirection,
    EmailLog,
    EmailType,
    IssueTag,
    PurchaseOrder,
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


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
    ) -> None:
        """Compose and send an email via Gmail API."""
        if not self._authenticated:
            logger.warning("Email service not authenticated — skipping send")
            return

        message = MIMEText(body)
        message["to"] = to
        message["from"] = settings.agent_email
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        await asyncio.to_thread(
            self._service.users().messages().send(userId="me", body={"raw": raw}).execute
        )
        logger.info("Email sent to {} — subject: {}", to, subject)

        if session and order_id:
            email_log = EmailLog(
                order_id=order_id,
                direction=EmailDirection.OUTBOUND.value,
                email_type=email_type,
                sender=settings.agent_email,
                recipient=to,
                subject=subject,
                sent_at=datetime.utcnow(),
            )
            session.add(email_log)

    async def send_confirmation(self, order: PurchaseOrder, session: AsyncSession) -> None:
        """Send auto-approval confirmation email."""
        log = logger.bind(correlation_id=str(order.id))
        log.info("Sending confirmation email to {}", order.sender_email)

        subject = f"PO {order.po_number or 'N/A'} — Approved"
        body = (
            f"Your purchase order has been automatically approved.\n\n"
            f"PO Number: {order.po_number or 'N/A'}\n"
            f"Vendor: {order.vendor_name or 'N/A'}\n"
            f"Total: {order.total_amount or 'N/A'} {order.currency or ''}\n"
            f"Delivery Date: {order.delivery_date or 'N/A'}\n\n"
            f"No action is required on your part."
        )
        if order.sender_email:
            await self.send_email(
                to=order.sender_email,
                subject=subject,
                body=body,
                order_id=order.id,
                email_type=EmailType.CONFIRMATION.value,
                session=session,
            )

    async def send_acknowledgment(self, order: PurchaseOrder, session: AsyncSession) -> None:
        """Send acknowledgment for flagged/rejected POs."""
        log = logger.bind(correlation_id=str(order.id))
        log.info("Sending acknowledgment email to {}", order.sender_email)

        subject = f"PO {order.po_number or 'N/A'} — Under Review"
        body = (
            f"Your purchase order has been received and is under review.\n\n"
            f"PO Number: {order.po_number or 'N/A'}\n"
            f"Vendor: {order.vendor_name or 'N/A'}\n"
            f"Total: {order.total_amount or 'N/A'} {order.currency or ''}\n\n"
            f"A reviewer will examine your order and you will be notified of the decision."
        )
        if order.sender_email:
            await self.send_email(
                to=order.sender_email,
                subject=subject,
                body=body,
                order_id=order.id,
                email_type=EmailType.ACKNOWLEDGMENT.value,
                session=session,
            )

    async def send_decision(
        self,
        order: PurchaseOrder,
        decision: str,
        comment: str | None,
        session: AsyncSession,
    ) -> None:
        """Send final decision email after reviewer acts."""
        from sqlmodel import select

        log = logger.bind(correlation_id=str(order.id))
        log.info("Sending decision email to {} — decision={}", order.sender_email, decision)

        if decision == "approve":
            subject = f"PO {order.po_number or 'N/A'} — Approved"
            body = (
                f"Your purchase order has been approved by a reviewer.\n\n"
                f"PO Number: {order.po_number or 'N/A'}\n"
                f"Vendor: {order.vendor_name or 'N/A'}\n"
                f"Total: {order.total_amount or 'N/A'} {order.currency or ''}\n"
            )
            if comment:
                body += f"\nReviewer comment: {comment}\n"
            email_type = EmailType.CONFIRMATION.value
        else:
            subject = f"PO {order.po_number or 'N/A'} — Rejected"
            body = (
                f"Your purchase order has been rejected after review.\n\n"
                f"PO Number: {order.po_number or 'N/A'}\n"
                f"Vendor: {order.vendor_name or 'N/A'}\n"
                f"Total: {order.total_amount or 'N/A'} {order.currency or ''}\n"
            )
            if comment:
                body += f"\nReviewer comment: {comment}\n"

            # Include issue tags for context
            result = await session.exec(select(IssueTag).where(IssueTag.order_id == order.id))
            tags = result.all()
            if tags:
                body += "\nIssues identified:\n"
                for t in tags:
                    body += f"  - {t.tag}: {t.description or 'No details'}\n"

            body += "\nPlease address the issues above and resubmit if appropriate."
            email_type = EmailType.REJECTION.value

        if order.sender_email:
            await self.send_email(
                to=order.sender_email,
                subject=subject,
                body=body,
                order_id=order.id,
                email_type=email_type,
                session=session,
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
                            received_at=datetime.utcnow().isoformat() + "Z",
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
