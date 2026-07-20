"""scope customers per business

Revision ID: f9e5895373e4
Revises: 837211a5205d
Create Date: 2026-07-02 16:50:28.609710

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9e5895373e4"
down_revision: Union[str, Sequence[str], None] = "837211a5205d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    # Step 1 — add user_id column to customers, nullable first so
    # existing rows don't violate NOT NULL before we fill them
    op.add_column("customers", sa.Column("user_id", sa.Integer(), nullable=True))

    # Step 2 — assign all existing customers to the first business (id=1)
    # Safe for dev: you only have one business in your DB right now.
    # In production you'd run a more targeted backfill script.
    op.execute("UPDATE customers SET user_id = 1 WHERE user_id IS NULL")

    # Step 3 — now that every row has a value, make it NOT NULL
    op.alter_column("customers", "user_id", nullable=False)

    # Step 4 — add the FK constraint pointing to users
    op.create_foreign_key(
        "fk_customers_user_id",
        "customers",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Step 5 — drop the old global unique constraint on phone_number alone
    op.drop_index("ix_customers_phone_number", table_name="customers")

    # Step 6 — add the new per-business unique constraint
    op.create_unique_constraint(
        "uq_customer_per_business", "customers", ["phone_number", "user_id"]
    )


def downgrade():
    """Downgrade schema."""
    op.drop_constraint("uq_customer_per_business", "customers", type_="unique")
    op.drop_constraint("fk_customers_user_id", "customers", type_="foreignkey")
    op.alter_column("customers", "user_id", nullable=True)
    op.drop_column("customers", "user_id")
    op.create_index(
        "ix_customers_phone_number", "customers", ["phone_number"], unique=True
    )
