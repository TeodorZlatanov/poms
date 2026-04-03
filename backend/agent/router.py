from models.enums import IssueSeverity, OrderStatus
from schemas.validation import IssueTagResult


def route_order(tags: list[IssueTagResult]) -> OrderStatus:
    """Determine order status based on aggregated issue tags.

    - No tags -> APPROVED
    - Soft tags only -> PENDING_REVIEW
    - Any hard tag -> REJECTED
    """
    if not tags:
        return OrderStatus.APPROVED

    has_hard = any(tag.severity == IssueSeverity.HARD for tag in tags)
    if has_hard:
        return OrderStatus.REJECTED

    return OrderStatus.PENDING_REVIEW
