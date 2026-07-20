"""merge migration heads

Revision ID: 8557c5fa405b
Revises: 9c1f2b4e6a7d, bf4ed52d9fca
Create Date: 2026-07-20 05:47:59.049956

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "8557c5fa405b"
down_revision: Union[str, Sequence[str], None] = ("9c1f2b4e6a7d", "bf4ed52d9fca")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
