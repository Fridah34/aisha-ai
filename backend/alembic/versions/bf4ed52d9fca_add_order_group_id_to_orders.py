"""add order_group_id to orders

Revision ID: bf4ed52d9fca
Revises: d2e4080255b2
Create Date: 2026-07-15 11:36:14.902821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bf4ed52d9fca'
down_revision: Union[str, Sequence[str], None] = 'd2e4080255b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("orders")]
    
    if "order_group_id" not in columns:
        op.add_column(
            "orders",
            sa.Column("order_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_index(
            "ix_orders_order_group_id", "orders", ["order_group_id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [i["name"] for i in inspector.get_indexes("orders")]
    columns = [c["name"] for c in inspector.get_columns("orders")]

    if "ix_orders_order_group_id" in indexes:
        op.drop_index("ix_orders_order_group_id", table_name="orders")
    if "order_group_id" in columns:
        op.drop_column("orders", "order_group_id")
