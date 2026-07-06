"""add_user_id_to_customers

Revision ID: e300988cdc0a
Revises: f9e5895373e4
Create Date: 2026-07-03 12:47:38.355008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e300988cdc0a'
down_revision: Union[str, Sequence[str], None] = 'f9e5895373e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # Check if user_id column already exists — skip add_column if so
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='customers' AND column_name='user_id'"
    ))
    if not result.fetchone():
        op.add_column('customers', sa.Column('user_id', sa.Integer(), nullable=True))

    # Backfill any rows missing user_id
    op.execute("UPDATE customers SET user_id = 1 WHERE user_id IS NULL")

    # Make NOT NULL if it isn't already
    op.alter_column('customers', 'user_id', nullable=False)

    # Add FK if it doesn't exist yet
    result = conn.execute(sa.text(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name='customers' AND constraint_name='fk_customers_user_id'"
    ))
    if not result.fetchone():
        op.create_foreign_key(
            'fk_customers_user_id',
            'customers', 'users',
            ['user_id'], ['id'],
            ondelete='CASCADE'
        )

    # Drop old unique index if it still exists
    result = conn.execute(sa.text(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename='customers' AND indexname='ix_customers_phone_number'"
    ))
    if result.fetchone():
        op.drop_index('ix_customers_phone_number', table_name='customers')

    # Add new per-business unique constraint if it doesn't exist
    result = conn.execute(sa.text(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_name='customers' AND constraint_name='uq_customer_per_business'"
    ))
    if not result.fetchone():
        op.create_unique_constraint(
            'uq_customer_per_business',
            'customers',
            ['phone_number', 'user_id']
        )



def downgrade():
    """Downgrade schema."""
    op.drop_constraint('uq_customer_per_business', 'customers', type_='unique')
    op.drop_constraint('fk_customers_user_id', 'customers', type_='foreignkey')
    op.alter_column('customers', 'user_id', nullable=True)
    op.drop_column('customers', 'user_id')
    op.create_index('ix_customers_phone_number', 'customers', ['phone_number'], unique=True)
