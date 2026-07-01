"""add_variant_fields_to_products

Revision ID: 59ede552dd88
Revises: a47010119730
Create Date: 2026-06-22 13:01:09.977514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59ede552dd88'
down_revision: Union[str, Sequence[str], None] = 'a47010119730'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() :
    """Upgrade schema."""
    op.add_column('products', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('products', sa.Column('variant_label', sa.String(50), nullable=True))
    op.add_column('products', sa.Column('variant_options', sa.String(300), nullable=True))
    op.add_column('products', sa.Column('unit', sa.String(50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'unit')
    op.drop_column('products', 'variant_options')
    op.drop_column('products', 'variant_label')
    op.drop_column('products', 'category')
