"""merge wiki chunks and main branch

Revision ID: eaf136d66d9e
Revises: 80698412d149, xxxx_add_wiki_chunks
Create Date: 2026-07-15 13:44:03.669550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eaf136d66d9e'
down_revision: Union[str, Sequence[str], None] = ('80698412d149', 'xxxx_add_wiki_chunks')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
