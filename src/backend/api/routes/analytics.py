from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import get_session
from models import IssueTag, OrderStatus, ProcessingLog, PurchaseOrder
from schemas.analytics import AnalyticsResponse, DayVolume, TagCount

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

TERMINAL_STATUSES = {OrderStatus.PROCESSING.value, OrderStatus.FAILED.value}


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    session: AsyncSession = Depends(get_session),
):
    # Total processed (exclude PROCESSING and FAILED)
    total_result = await session.exec(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(col(PurchaseOrder.status).notin_(TERMINAL_STATUSES))
    )
    total_processed = total_result.one()

    # By status
    status_result = await session.exec(
        select(PurchaseOrder.status, func.count()).group_by(PurchaseOrder.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Approval rate
    approved_count = by_status.get(OrderStatus.APPROVED.value, 0)
    approval_rate = approved_count / total_processed if total_processed > 0 else 0.0

    # Common tags (top 10)
    tags_result = await session.exec(
        select(IssueTag.tag, func.count())
        .group_by(IssueTag.tag)
        .order_by(func.count().desc())
        .limit(10)
    )
    common_tags = [TagCount(tag=row[0], count=row[1]) for row in tags_result.all()]

    # Average processing time (sum duration per order, then avg across orders)
    subquery = (
        select(
            ProcessingLog.order_id,
            func.sum(ProcessingLog.duration_ms).label("total_ms"),
        )
        .group_by(ProcessingLog.order_id)
        .subquery()
    )
    avg_result = await session.exec(select(func.avg(subquery.c.total_ms)))
    avg_processing_time_ms = avg_result.one() or 0.0

    # Volume by day (last 30 days)
    volume_result = await session.exec(
        select(
            cast(PurchaseOrder.created_at, Date).label("day"),
            func.count(),
        )
        .group_by("day")
        .order_by(cast(PurchaseOrder.created_at, Date).desc())
        .limit(30)
    )
    volume_by_day = [DayVolume(date=str(row[0]), count=row[1]) for row in volume_result.all()]

    return AnalyticsResponse(
        total_processed=total_processed,
        by_status=by_status,
        approval_rate=round(approval_rate, 4),
        common_tags=common_tags,
        avg_processing_time_ms=round(float(avg_processing_time_ms), 2),
        volume_by_day=volume_by_day,
    )
