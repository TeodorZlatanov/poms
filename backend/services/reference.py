from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.reference import ApprovedVendor, ProcurementPolicy, ProductCatalog


async def lookup_vendor(session: AsyncSession, name: str) -> ApprovedVendor | None:
    """Exact case-insensitive vendor lookup."""
    stmt = select(ApprovedVendor).where(func.lower(ApprovedVendor.name) == name.lower().strip())
    result = await session.exec(stmt)
    return result.first()


async def fuzzy_match_vendor(
    session: AsyncSession, name: str, threshold: float = 0.4
) -> ApprovedVendor | None:
    """Fuzzy vendor match using pg_trgm similarity."""
    stmt = (
        select(ApprovedVendor)
        .where(func.similarity(ApprovedVendor.name, name) > threshold)
        .order_by(func.similarity(ApprovedVendor.name, name).desc())
        .limit(1)
    )
    result = await session.exec(stmt)
    return result.first()


async def lookup_product_by_sku(session: AsyncSession, sku: str) -> ProductCatalog | None:
    """Exact SKU lookup (case-insensitive)."""
    stmt = select(ProductCatalog).where(func.upper(ProductCatalog.sku) == sku.upper().strip())
    result = await session.exec(stmt)
    return result.first()


async def get_department_limit(session: AsyncSession, department: str) -> float | None:
    """Get the per-order spending limit for a department."""
    stmt = select(ProcurementPolicy).where(
        ProcurementPolicy.policy_type == "department_limit",
        func.lower(ProcurementPolicy.department) == department.lower().strip(),
    )
    result = await session.exec(stmt)
    policy = result.first()
    return policy.threshold_value if policy else None


async def get_allowed_payment_terms(session: AsyncSession) -> list[str]:
    """Get the list of allowed payment terms."""
    stmt = select(ProcurementPolicy).where(
        ProcurementPolicy.policy_type == "payment_terms",
    )
    result = await session.exec(stmt)
    policy = result.first()
    if policy and policy.allowed_values:
        return policy.allowed_values.get("terms", [])
    return ["net 15", "net 30", "due on receipt"]
