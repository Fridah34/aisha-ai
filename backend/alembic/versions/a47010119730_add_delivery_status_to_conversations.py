"""add_delivery_status_to_conversations

Revision ID: a47010119730
Revises: 66ec7ec1e49b
Create Date: 2026-06-19 23:29:12.545052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a47010119730'
down_revision: Union[str, Sequence[str], None] = '66ec7ec1e49b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    op.add_column(
        'conversations',
        sa.Column(
            'delivery_status',
            sa.String(20),
            nullable=True,
            server_default=None,
        )
    )
    


def downgrade():
    """Downgrade schema."""
    op.drop_column('conversations', 'delivery_status')
