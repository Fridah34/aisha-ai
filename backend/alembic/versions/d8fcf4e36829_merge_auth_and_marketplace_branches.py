"""merge auth and marketplace branches

Revision ID: d8fcf4e36829
Revises: 34c4a812b9a8, 80698412d149
Create Date: 2026-07-09 11:58:41.179377

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "d8fcf4e36829"
down_revision: Union[str, Sequence[str], None] = ("34c4a812b9a8", "80698412d149")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
