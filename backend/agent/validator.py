from loguru import logger

from models.enums import IssueSeverity, IssueTagType, ValidationCheckType, ValidationResult
from schemas.extraction import PurchaseOrderExtraction
from schemas.validation import IssueTagResult, ValidationCheckResult
from services.knowledge import knowledge_base


async def validate_vendor(extraction: PurchaseOrderExtraction) -> ValidationCheckResult:
    """Check vendor against approved vendor registry."""
    tags: list[IssueTagResult] = []
    vendor_name = extraction.vendor.name

    # Try exact match
    vendor = knowledge_base.lookup_vendor(vendor_name)
    if vendor:
        if vendor["contract_status"] == "expired":
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.EXPIRED_CONTRACT,
                    severity=IssueSeverity.HARD,
                    description=f"Vendor '{vendor_name}' has an expired contract "
                    f"(expired {vendor.get('contract_expiry_date', 'unknown')})",
                )
            )
            result = ValidationResult.FAIL
        else:
            result = ValidationResult.PASS
        logger.bind(step="validation").info(
            "Vendor exact match: {} — status={}", vendor_name, vendor["contract_status"]
        )
    else:
        # Try fuzzy match
        fuzzy = knowledge_base.fuzzy_match_vendor(vendor_name)
        if fuzzy:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.VENDOR_FUZZY_MATCH,
                    severity=IssueSeverity.SOFT,
                    description=f"Vendor '{vendor_name}' is a close match to "
                    f"registered vendor '{fuzzy['name']}'",
                )
            )
            result = ValidationResult.WARNING
            logger.bind(step="validation").info(
                "Vendor fuzzy match: {} → {}", vendor_name, fuzzy["name"]
            )
        else:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.UNKNOWN_VENDOR,
                    severity=IssueSeverity.HARD,
                    description=f"Vendor '{vendor_name}' not found in approved vendor registry",
                )
            )
            result = ValidationResult.FAIL
            logger.bind(step="validation").warning("Unknown vendor: {}", vendor_name)

    return ValidationCheckResult(
        check_type=ValidationCheckType.VENDOR,
        result=result,
        details={"vendor_name": vendor_name, "match_type": result.value},
        tags=tags,
    )


async def validate_prices(extraction: PurchaseOrderExtraction) -> ValidationCheckResult:
    """Check line item prices against product catalog."""
    tags: list[IssueTagResult] = []
    details: dict = {"items_checked": 0, "mismatches": []}
    worst_result = ValidationResult.PASS

    for item in extraction.line_items:
        if not item.sku:
            continue

        product = knowledge_base.lookup_product_by_sku(item.sku)
        if not product:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.UNKNOWN_PRODUCT,
                    severity=IssueSeverity.SOFT,
                    description=f"SKU '{item.sku}' not found in product catalog",
                )
            )
            worst_result = _worse(worst_result, ValidationResult.WARNING)
            continue

        details["items_checked"] += 1

        if item.unit_price is None:
            continue

        catalog_price = product["unit_price"]
        if catalog_price <= 0:
            continue

        deviation = (item.unit_price - catalog_price) / catalog_price

        # Below catalog price is fine (negotiated discount)
        if deviation <= 0.10:
            continue

        tags.append(
            IssueTagResult(
                tag=IssueTagType.PRICE_MISMATCH,
                severity=IssueSeverity.SOFT,
                description=f"SKU '{item.sku}' priced at {item.unit_price} vs catalog "
                f"{catalog_price} ({deviation:+.1%} deviation)",
            )
        )
        details["mismatches"].append(
            {
                "sku": item.sku,
                "po_price": item.unit_price,
                "catalog_price": catalog_price,
                "deviation_pct": round(deviation * 100, 1),
            }
        )
        worst_result = _worse(worst_result, ValidationResult.WARNING)

    return ValidationCheckResult(
        check_type=ValidationCheckType.PRICE,
        result=worst_result,
        details=details,
        tags=tags,
    )


async def validate_policy(extraction: PurchaseOrderExtraction) -> ValidationCheckResult:
    """Check against procurement policies (dept limits, payment terms)."""
    tags: list[IssueTagResult] = []
    details: dict = {}
    worst_result = ValidationResult.PASS

    # Check department spending limit
    department = extraction.requester.department if extraction.requester else None
    if department and extraction.total_amount is not None:
        limit = knowledge_base.get_department_limit(department)
        if limit is not None:
            details["department"] = department
            details["limit"] = limit
            details["total_amount"] = extraction.total_amount
            if extraction.total_amount > limit:
                tags.append(
                    IssueTagResult(
                        tag=IssueTagType.OVER_LIMIT,
                        severity=IssueSeverity.HARD,
                        description=f"Total {extraction.total_amount} EUR exceeds "
                        f"{department} department limit of {limit} EUR",
                    )
                )
                worst_result = _worse(worst_result, ValidationResult.FAIL)

    # Check payment terms
    if extraction.payment_terms:
        terms = extraction.payment_terms.strip().lower()
        details["payment_terms"] = extraction.payment_terms
        allowed = {"net 15", "net 30", "due on receipt"}
        if terms in allowed:
            pass  # OK
        elif "net" in terms:
            # Parse net days
            try:
                days = int(terms.replace("net", "").strip())
                if days > 30:
                    tags.append(
                        IssueTagResult(
                            tag=IssueTagType.TERMS_VIOLATION,
                            severity=IssueSeverity.HARD,
                            description=f"Payment terms '{extraction.payment_terms}' exceed "
                            f"maximum allowed Net 30",
                        )
                    )
                    worst_result = _worse(worst_result, ValidationResult.FAIL)
            except ValueError:
                tags.append(
                    IssueTagResult(
                        tag=IssueTagType.TERMS_VIOLATION,
                        severity=IssueSeverity.SOFT,
                        description=f"Unrecognized payment terms: '{extraction.payment_terms}'",
                    )
                )
                worst_result = _worse(worst_result, ValidationResult.WARNING)
        else:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.TERMS_VIOLATION,
                    severity=IssueSeverity.SOFT,
                    description=f"Unrecognized payment terms: '{extraction.payment_terms}'",
                )
            )
            worst_result = _worse(worst_result, ValidationResult.WARNING)

    return ValidationCheckResult(
        check_type=ValidationCheckType.POLICY,
        result=worst_result,
        details=details,
        tags=tags,
    )


async def validate_completeness(extraction: PurchaseOrderExtraction) -> ValidationCheckResult:
    """Rule-based check for required fields. No LLM needed."""
    tags: list[IssueTagResult] = []

    # Hard-required fields
    hard_checks = [
        (extraction.po_number, "po_number"),
        (extraction.vendor.name, "vendor.name"),
        (extraction.total_amount is not None, "total_amount"),
        (extraction.currency, "currency"),
        (extraction.delivery_date, "delivery_date"),
    ]
    for value, field_name in hard_checks:
        if not value:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.MISSING_FIELD,
                    severity=IssueSeverity.HARD,
                    description=f"Required field '{field_name}' is missing",
                )
            )

    # line_items must be non-empty
    if not extraction.line_items:
        tags.append(
            IssueTagResult(
                tag=IssueTagType.MISSING_FIELD,
                severity=IssueSeverity.HARD,
                description="Required field 'line_items' is empty",
            )
        )

    # Soft-recommended fields
    if not extraction.vendor.contact:
        tags.append(
            IssueTagResult(
                tag=IssueTagType.MISSING_FIELD,
                severity=IssueSeverity.SOFT,
                description="Recommended field 'vendor.contact' is missing",
            )
        )
    if not extraction.requester:
        tags.append(
            IssueTagResult(
                tag=IssueTagType.MISSING_FIELD,
                severity=IssueSeverity.SOFT,
                description="Recommended field 'requester' is missing",
            )
        )
    if not extraction.payment_terms:
        tags.append(
            IssueTagResult(
                tag=IssueTagType.MISSING_FIELD,
                severity=IssueSeverity.SOFT,
                description="Recommended field 'payment_terms' is missing",
            )
        )
    # Check individual line items for missing SKU/unit_price
    for i, item in enumerate(extraction.line_items):
        if not item.sku:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.MISSING_FIELD,
                    severity=IssueSeverity.SOFT,
                    description=f"Recommended field 'line_items[{i}].sku' is missing",
                )
            )
        if item.unit_price is None:
            tags.append(
                IssueTagResult(
                    tag=IssueTagType.MISSING_FIELD,
                    severity=IssueSeverity.SOFT,
                    description=f"Recommended field 'line_items[{i}].unit_price' is missing",
                )
            )

    # Determine overall result
    hard_tags = [t for t in tags if t.severity == IssueSeverity.HARD]
    soft_tags = [t for t in tags if t.severity == IssueSeverity.SOFT]
    if hard_tags:
        result = ValidationResult.FAIL
    elif soft_tags:
        result = ValidationResult.WARNING
    else:
        result = ValidationResult.PASS

    return ValidationCheckResult(
        check_type=ValidationCheckType.COMPLETENESS,
        result=result,
        details={
            "hard_missing": [t.description for t in hard_tags],
            "soft_missing": [t.description for t in soft_tags],
        },
        tags=tags,
    )


def _worse(current: ValidationResult, new: ValidationResult) -> ValidationResult:
    """Return the worse of two validation results."""
    order = {ValidationResult.PASS: 0, ValidationResult.WARNING: 1, ValidationResult.FAIL: 2}
    return current if order[current] >= order[new] else new
