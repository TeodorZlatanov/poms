"""Seed reference data tables from knowledge/ JSON and policy files.

Usage: cd backend && uv run python -m scripts.seed_reference_data
"""

import asyncio
import json
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import async_session_factory
from models.reference import ApprovedVendor, ProcurementPolicy, ProductCatalog

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


async def seed_vendors(session: AsyncSession) -> int:
    """Seed approved_vendors from vendors.json. Returns count of inserted rows."""
    existing = await session.exec(select(ApprovedVendor).limit(1))
    if existing.first():
        print("approved_vendors already seeded, skipping")
        return 0

    vendors_path = KNOWLEDGE_DIR / "vendors.json"
    with open(vendors_path) as f:
        data = json.load(f)

    count = 0
    for v in data["approved_vendors"]:
        vendor = ApprovedVendor(
            vendor_id=v["id"],
            name=v["name"],
            contact_email=v.get("contact_email"),
            contract_status=v["contract_status"],
            contract_expiry_date=v.get("contract_expiry_date"),
            address=v.get("address"),
            payment_terms=v["payment_terms"],
        )
        session.add(vendor)
        count += 1

    await session.flush()
    print(f"Seeded {count} vendors")
    return count


async def seed_products(session: AsyncSession) -> int:
    """Seed product_catalog from catalog.json."""
    existing = await session.exec(select(ProductCatalog).limit(1))
    if existing.first():
        print("product_catalog already seeded, skipping")
        return 0

    catalog_path = KNOWLEDGE_DIR / "catalog.json"
    with open(catalog_path) as f:
        data = json.load(f)

    count = 0
    for p in data["products"]:
        product = ProductCatalog(
            sku=p["sku"],
            description=p["description"],
            category=p["category"],
            unit_price=p["unit_price"],
            currency=p["currency"],
            unit_of_measure=p["unit_of_measure"],
            min_order_quantity=p["min_order_quantity"],
        )
        session.add(product)
        count += 1

    await session.flush()
    print(f"Seeded {count} products")
    return count


async def seed_policies(session: AsyncSession) -> int:
    """Seed procurement_policies with structured policy rules."""
    existing = await session.exec(select(ProcurementPolicy).limit(1))
    if existing.first():
        print("procurement_policies already seeded, skipping")
        return 0

    policies = [
        # Department spending limits
        ProcurementPolicy(
            policy_type="department_limit",
            department="Engineering",
            threshold_value=5000.0,
            description="Engineering department per-order spending limit",
        ),
        ProcurementPolicy(
            policy_type="department_limit",
            department="Marketing",
            threshold_value=5000.0,
            description="Marketing department per-order spending limit",
        ),
        ProcurementPolicy(
            policy_type="department_limit",
            department="Operations",
            threshold_value=10000.0,
            description="Operations department per-order spending limit",
        ),
        ProcurementPolicy(
            policy_type="department_limit",
            department="Finance",
            threshold_value=15000.0,
            description="Finance department per-order spending limit",
        ),
        ProcurementPolicy(
            policy_type="department_limit",
            department="HR",
            threshold_value=3000.0,
            description="HR department per-order spending limit",
        ),
        # Payment terms
        ProcurementPolicy(
            policy_type="payment_terms",
            allowed_values={"terms": ["net 15", "net 30", "due on receipt"]},
            threshold_value=30.0,
            description="Maximum payment terms: Net 30. Allowed: Net 15, Net 30, Due on Receipt",
        ),
        # Minimum order value
        ProcurementPolicy(
            policy_type="min_order_value",
            threshold_value=50.0,
            description="Minimum order value EUR 50.00",
        ),
        # Approval thresholds
        ProcurementPolicy(
            policy_type="approval_threshold",
            threshold_value=500.0,
            description="Orders up to EUR 500: automatic approval",
        ),
        ProcurementPolicy(
            policy_type="approval_threshold",
            threshold_value=2500.0,
            description="Orders EUR 500-2500: department manager approval",
        ),
        ProcurementPolicy(
            policy_type="approval_threshold",
            threshold_value=10000.0,
            description="Orders EUR 2500-10000: department head + Finance review",
        ),
        # Allowed currencies
        ProcurementPolicy(
            policy_type="allowed_currencies",
            allowed_values={"currencies": ["EUR", "BGN", "USD"]},
            description="Approved currencies: EUR (preferred), BGN, USD",
        ),
    ]

    for p in policies:
        session.add(p)

    await session.flush()
    print(f"Seeded {len(policies)} policy rules")
    return len(policies)


async def main() -> None:
    async with async_session_factory() as session:
        await seed_vendors(session)
        await seed_products(session)
        await seed_policies(session)
        await session.commit()
        print("Reference data seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
