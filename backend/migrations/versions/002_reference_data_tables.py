"""reference data tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "approved_vendors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vendor_id", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("contract_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column(
            "contract_expiry_date", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True
        ),
        sa.Column("address", sa.JSON(), nullable=True),
        sa.Column("payment_terms", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vendor_id"),
    )
    # Trigram index for fuzzy vendor name matching
    op.execute(
        "CREATE INDEX ix_approved_vendors_name_trgm ON approved_vendors "
        "USING gin (name gin_trgm_ops)"
    )

    op.create_table(
        "product_catalog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sku", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("unit_of_measure", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("min_order_quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )

    op.create_table(
        "procurement_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_type", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("department", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("allowed_values", sa.JSON(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("procurement_policies")
    op.drop_table("product_catalog")
    op.execute("DROP INDEX IF EXISTS ix_approved_vendors_name_trgm")
    op.drop_table("approved_vendors")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
