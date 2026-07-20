"""add_image_url_and_upsell_text_to_products

Revision ID: 837211a5205d
Revises: 59ede552dd88
Create Date: 2026-06-23 04:57:44.306878

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "837211a5205d"
down_revision: Union[str, Sequence[str], None] = "59ede552dd88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    op.add_column("products", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("products", sa.Column("upsell_text", sa.Text, nullable=True))


def downgrade():
    """Downgrade schema."""
    op.drop_column("products", "upsell_text")
    op.drop_column("products", "image_url")
