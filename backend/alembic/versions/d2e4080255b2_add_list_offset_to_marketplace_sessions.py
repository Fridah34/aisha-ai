"""add list_offset to marketplace_sessions

Revision ID: d2e4080255b2
Revises: 338e8a8abd83
Create Date: 2026-07-14 13:11:38.756626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e4080255b2'
down_revision: Union[str, Sequence[str], None] = '338e8a8abd83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col["name"] for col in inspector.get_columns("marketplace_sessions")]
    
    if "list_offset" not in existing_columns:
        op.add_column(
            "marketplace_sessions",
            sa.Column("list_offset", sa.Integer(), nullable=False, server_default="0"),
        )
        print("[Migration] Added list_offset to marketplace_sessions")
    else:
        print("[Migration] list_offset already exists on marketplace_sessions - skipping")
        


def downgrade():
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col["name"] for col in inspector.get_columns("marketplace_sessions")]
 
    if "list_offset" in existing_columns:
        op.drop_column("marketplace_sessions", "list_offset")
        print("[Migration] Dropped list_offset from marketplace_sessions")
    else:
        print("[Migration] list_offset already absent from marketplace_sessions — skipping")
