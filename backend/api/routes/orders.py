import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_session
from models import (
    EmailLog,
    IssueTag,
    ProcessingLog,
    PurchaseOrder,
    ReviewDecision,
    ValidationCheck,
)
from schemas.orders import (
    EmailDetail,
    IssueTagDetail,
    OrderDetailResponse,
    OrderListResponse,
    OrderSummary,
    ProcessingLogDetail,
    ReviewDetail,
    ValidationCheckDetail,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    status: str | None = Query(default=None),
    vendor: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    query = select(PurchaseOrder)
    count_query = select(func.count()).select_from(PurchaseOrder)

    if status:
        query = query.where(PurchaseOrder.status == status)
        count_query = count_query.where(PurchaseOrder.status == status)
    if vendor:
        query = query.where(PurchaseOrder.vendor_name.ilike(f"%{vendor}%"))
        count_query = count_query.where(PurchaseOrder.vendor_name.ilike(f"%{vendor}%"))

    # Get total count
    total_result = await session.exec(count_query)
    total = total_result.one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(PurchaseOrder.created_at.desc()).offset(offset).limit(page_size)
    result = await session.exec(query)
    orders = result.all()

    # Get issue tags for each order
    items = []
    for order in orders:
        tag_result = await session.exec(select(IssueTag.tag).where(IssueTag.order_id == order.id))
        tag_names = list(tag_result.all())
        summary = OrderSummary(
            id=order.id,
            po_number=order.po_number,
            vendor_name=order.vendor_name,
            total_amount=order.total_amount,
            currency=order.currency,
            status=order.status,
            issue_tags=tag_names,
            created_at=order.created_at,
        )
        items.append(summary)

    return OrderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.exec(select(PurchaseOrder).where(PurchaseOrder.id == order_id))
    order = result.first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Fetch related data
    validations_result = await session.exec(
        select(ValidationCheck).where(ValidationCheck.order_id == order_id)
    )
    tags_result = await session.exec(select(IssueTag).where(IssueTag.order_id == order_id))
    emails_result = await session.exec(select(EmailLog).where(EmailLog.order_id == order_id))
    logs_result = await session.exec(
        select(ProcessingLog).where(ProcessingLog.order_id == order_id)
    )
    review_result = await session.exec(
        select(ReviewDecision).where(ReviewDecision.order_id == order_id)
    )

    validations = validations_result.all()
    tags = tags_result.all()
    emails = emails_result.all()
    logs = logs_result.all()
    review = review_result.first()

    return OrderDetailResponse(
        id=order.id,
        po_number=order.po_number,
        po_date=order.po_date,
        vendor_name=order.vendor_name,
        vendor_contact=order.vendor_contact,
        requester_name=order.requester_name,
        requester_department=order.requester_department,
        line_items=order.line_items,
        total_amount=order.total_amount,
        currency=order.currency,
        delivery_date=order.delivery_date,
        payment_terms=order.payment_terms,
        status=order.status,
        confidence_score=order.confidence_score,
        original_filename=order.original_filename,
        sender_email=order.sender_email,
        created_at=order.created_at,
        updated_at=order.updated_at,
        validation_results=[ValidationCheckDetail.model_validate(v) for v in validations],
        issue_tags=[IssueTagDetail.model_validate(t) for t in tags],
        emails=[EmailDetail.model_validate(e) for e in emails],
        processing_logs=[ProcessingLogDetail.model_validate(lg) for lg in logs],
        review=ReviewDetail.model_validate(review) if review else None,
    )
