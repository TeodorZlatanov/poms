from agent.router import route_order
from models.enums import IssueSeverity, IssueTagType, OrderStatus
from schemas.validation import IssueTagResult


def _tag(tag_type: IssueTagType, severity: IssueSeverity) -> IssueTagResult:
    return IssueTagResult(tag=tag_type, severity=severity, description="test")


class TestRouteOrder:
    def test_no_tags_returns_approved(self):
        assert route_order([]) == OrderStatus.APPROVED

    def test_soft_tags_only_returns_pending_review(self):
        tags = [_tag(IssueTagType.VENDOR_FUZZY_MATCH, IssueSeverity.SOFT)]
        assert route_order(tags) == OrderStatus.PENDING_REVIEW

    def test_hard_tag_returns_rejected(self):
        tags = [_tag(IssueTagType.UNKNOWN_VENDOR, IssueSeverity.HARD)]
        assert route_order(tags) == OrderStatus.REJECTED

    def test_mixed_soft_and_hard_returns_rejected(self):
        tags = [
            _tag(IssueTagType.PRICE_MISMATCH, IssueSeverity.SOFT),
            _tag(IssueTagType.OVER_LIMIT, IssueSeverity.HARD),
        ]
        assert route_order(tags) == OrderStatus.REJECTED

    def test_multiple_soft_tags_returns_pending_review(self):
        tags = [
            _tag(IssueTagType.VENDOR_FUZZY_MATCH, IssueSeverity.SOFT),
            _tag(IssueTagType.PRICE_MISMATCH, IssueSeverity.SOFT),
            _tag(IssueTagType.UNKNOWN_PRODUCT, IssueSeverity.SOFT),
        ]
        assert route_order(tags) == OrderStatus.PENDING_REVIEW
