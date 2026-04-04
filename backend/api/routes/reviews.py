import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_session
from models import OrderStatus, PurchaseOrder, ReviewDecision, ReviewDecisionType
from schemas.reviews import ReviewRequest, ReviewResponse
from services.email import email_service

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

REVIEWABLE_STATUSES = {OrderStatus.PENDING_REVIEW.value, OrderStatus.REJECTED.value}


@router.post("/{order_id}", response_model=ReviewResponse)
async def submit_review(
    order_id: uuid.UUID,
    request: ReviewRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in REVIEWABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Order status '{order.status}' is not reviewable",
        )

    # Map decision to status
    if request.decision == "approve":
        new_status = OrderStatus.APPROVED.value
        decision_type = ReviewDecisionType.APPROVE.value
    else:
        new_status = OrderStatus.REJECTED.value
        decision_type = ReviewDecisionType.REJECT.value

    # Create review decision
    review = ReviewDecision(
        order_id=order_id,
        decision=decision_type,
        comment=request.comment,
    )
    session.add(review)

    # Update order status
    order.status = new_status
    order.updated_at = datetime.utcnow()
    session.add(order)

    await session.flush()

    # Send decision email (best-effort)
    email_sent = False
    try:
        await email_service.send_decision(order, request.decision, request.comment, session)
        email_sent = True
    except Exception:
        logger.warning("Failed to send decision email for order {}", order_id)

    await session.commit()

    return ReviewResponse(
        id=review.id,
        order_id=order_id,
        decision=decision_type,
        comment=request.comment,
        decided_at=review.decided_at,
        email_sent=email_sent,
    )
