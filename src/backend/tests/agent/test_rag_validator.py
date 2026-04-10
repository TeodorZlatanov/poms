from agent.rag_validator import (
    RAGNewTag,
    RAGTagAdjustment,
    RAGValidationResult,
    apply_rag_adjustments,
)
from models.enums import IssueSeverity, IssueTagType
from schemas.validation import IssueTagResult


def _tag(tag_type: IssueTagType, severity: IssueSeverity, desc: str = "test") -> IssueTagResult:
    return IssueTagResult(tag=tag_type, severity=severity, description=desc)


class TestApplyRagAdjustments:
    def test_keep_action_preserves_tag(self):
        tags = [_tag(IssueTagType.PRICE_MISMATCH, IssueSeverity.SOFT)]
        rag_result = RAGValidationResult(
            adjustments=[
                RAGTagAdjustment(
                    original_tag="PRICE_MISMATCH", action="keep", reasoning="valid flag"
                )
            ],
            new_tags=[],
            summary="Kept",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 1
        assert result[0].tag == IssueTagType.PRICE_MISMATCH
        assert result[0].severity == IssueSeverity.SOFT

    def test_remove_action_drops_tag(self):
        tags = [_tag(IssueTagType.VENDOR_FUZZY_MATCH, IssueSeverity.SOFT)]
        rag_result = RAGValidationResult(
            adjustments=[
                RAGTagAdjustment(
                    original_tag="VENDOR_FUZZY_MATCH",
                    action="remove",
                    reasoning="Known abbreviation",
                )
            ],
            new_tags=[],
            summary="Removed",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 0

    def test_downgrade_changes_severity(self):
        tags = [_tag(IssueTagType.EXPIRED_CONTRACT, IssueSeverity.HARD)]
        rag_result = RAGValidationResult(
            adjustments=[
                RAGTagAdjustment(
                    original_tag="EXPIRED_CONTRACT",
                    action="downgrade",
                    adjusted_severity="SOFT",
                    reasoning="90-day grace period applies",
                )
            ],
            new_tags=[],
            summary="Downgraded",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 1
        assert result[0].severity == IssueSeverity.SOFT
        assert "RAG:" in result[0].description

    def test_upgrade_changes_severity(self):
        tags = [_tag(IssueTagType.TERMS_VIOLATION, IssueSeverity.SOFT)]
        rag_result = RAGValidationResult(
            adjustments=[
                RAGTagAdjustment(
                    original_tag="TERMS_VIOLATION",
                    action="upgrade",
                    adjusted_severity="HARD",
                    reasoning="Net 60 from domestic vendor without framework agreement",
                )
            ],
            new_tags=[],
            summary="Upgraded",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 1
        assert result[0].severity == IssueSeverity.HARD

    def test_new_tags_are_added(self):
        tags = [_tag(IssueTagType.PRICE_MISMATCH, IssueSeverity.SOFT)]
        rag_result = RAGValidationResult(
            adjustments=[],
            new_tags=[
                RAGNewTag(
                    tag="MISSING_FIELD",
                    severity="SOFT",
                    description="Safety sign-off missing",
                    reasoning="Safety equipment requires Engineering sign-off",
                )
            ],
            summary="Added new tag",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 2
        new = [t for t in result if "Safety" in t.description]
        assert len(new) == 1
        assert new[0].tag == IssueTagType.MISSING_FIELD

    def test_no_adjustment_keeps_original(self):
        """Tags without matching adjustments are kept as-is."""
        tags = [
            _tag(IssueTagType.PRICE_MISMATCH, IssueSeverity.SOFT),
            _tag(IssueTagType.UNKNOWN_VENDOR, IssueSeverity.HARD),
        ]
        rag_result = RAGValidationResult(
            adjustments=[
                RAGTagAdjustment(
                    original_tag="PRICE_MISMATCH", action="remove", reasoning="Volume discount"
                )
            ],
            new_tags=[],
            summary="Partial adjustment",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 1
        assert result[0].tag == IssueTagType.UNKNOWN_VENDOR

    def test_invalid_new_tag_type_skipped(self):
        """RAG-suggested tags with invalid enum values are silently skipped."""
        tags = []
        rag_result = RAGValidationResult(
            adjustments=[],
            new_tags=[
                RAGNewTag(
                    tag="INVALID_TAG_TYPE",
                    severity="SOFT",
                    description="Should be skipped",
                    reasoning="Bad tag",
                )
            ],
            summary="Invalid tag",
        )
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 0

    def test_empty_adjustments_and_tags(self):
        tags = []
        rag_result = RAGValidationResult(adjustments=[], new_tags=[], summary="Clean")
        result = apply_rag_adjustments(tags, rag_result)
        assert len(result) == 0
