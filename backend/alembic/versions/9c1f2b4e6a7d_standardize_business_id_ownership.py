"""standardize business ownership columns to business_id

Revision ID: 9c1f2b4e6a7d
Revises: 783dbf9cad69
Create Date: 2026-07-20 05:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c1f2b4e6a7d"
down_revision: Union[str, Sequence[str], None] = "783dbf9cad69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_index(inspector: sa.Inspector, table: str, index_name: str) -> bool:
    return any(i["name"] == index_name for i in inspector.get_indexes(table))


def _has_constraint(inspector: sa.Inspector, table: str, name: str) -> bool:
    return any(c["name"] == name for c in inspector.get_unique_constraints(table))


def _drop_foreign_keys_for_column(
    inspector: sa.Inspector, table: str, column: str
) -> None:
    for fk in inspector.get_foreign_keys(table):
        if fk.get("constrained_columns") == [column] and fk.get("name"):
            op.drop_constraint(fk["name"], table, type_="foreignkey")


def _has_business_fk(inspector: sa.Inspector, table: str) -> bool:
    for fk in inspector.get_foreign_keys(table):
        if (
            fk.get("constrained_columns") == ["business_id"]
            and fk.get("referred_table") == "users"
        ):
            return True
    return False


def _rename_user_to_business_if_needed(table: str) -> None:
    inspector = sa.inspect(op.get_bind())
    has_user = _has_column(inspector, table, "user_id")
    has_business = _has_column(inspector, table, "business_id")

    if has_user and not has_business:
        _drop_foreign_keys_for_column(inspector, table, "user_id")
        op.alter_column(table, "user_id", new_column_name="business_id")
    elif has_user and has_business:
        # Defensive backfill path for mixed transitional schemas.
        op.execute(
            sa.text(
                f"UPDATE {table} SET business_id = user_id WHERE business_id IS NULL"
            )
        )


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    for table in ("categories", "orders", "products", "customers"):
        if table in inspector.get_table_names():
            _rename_user_to_business_if_needed(table)

    inspector = sa.inspect(conn)

    fk_specs = {
        "categories": "CASCADE",
        "products": "CASCADE",
        "customers": "CASCADE",
        "orders": "SET NULL",
    }
    for table, ondelete in fk_specs.items():
        if table not in inspector.get_table_names() or not _has_column(
            inspector, table, "business_id"
        ):
            continue
        if not _has_business_fk(inspector, table):
            op.create_foreign_key(
                f"fk_{table}_business_id_users",
                table,
                "users",
                ["business_id"],
                ["id"],
                ondelete=ondelete,
            )

    for table in ("categories", "orders", "products", "customers"):
        if table not in inspector.get_table_names() or not _has_column(
            inspector, table, "business_id"
        ):
            continue
        if _has_index(inspector, table, f"ix_{table}_user_id"):
            op.drop_index(f"ix_{table}_user_id", table_name=table)
        if not _has_index(inspector, table, f"ix_{table}_business_id"):
            op.create_index(
                f"ix_{table}_business_id", table, ["business_id"], unique=False
            )

    if "customers" in inspector.get_table_names():
        if _has_column(inspector, "customers", "business_id") and not _has_constraint(
            inspector, "customers", "uq_customer_per_business"
        ):
            op.create_unique_constraint(
                "uq_customer_per_business",
                "customers",
                ["phone_number", "business_id"],
            )

    if "categories" in inspector.get_table_names():
        if _has_column(inspector, "categories", "business_id") and not _has_constraint(
            inspector, "categories", "uq_category_per_business"
        ):
            op.create_unique_constraint(
                "uq_category_per_business",
                "categories",
                ["name", "business_id"],
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in ("categories", "orders", "products", "customers"):
        if table not in inspector.get_table_names():
            continue
        if _has_column(inspector, table, "business_id") and not _has_column(
            inspector, table, "user_id"
        ):
            _drop_foreign_keys_for_column(inspector, table, "business_id")
            op.alter_column(table, "business_id", new_column_name="user_id")
