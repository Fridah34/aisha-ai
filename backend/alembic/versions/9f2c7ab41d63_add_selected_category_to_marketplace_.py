"""add selected_category to marketplace_sessions

Splits the category slot out of marketplace_sessions.selected_business_type.

handle_marketplace_step used to assign the chosen Category *name* to
selected_business_type (e.g. 'Handbag'), and every downstream consumer read it
back as `category_name=`. That left the real business classification with
nowhere to live and made the column impossible to reason about. Category
selection now has its own column.

The data migration moves existing values across: any selected_business_type
that matches a real categories.name row is a category that was parked in the
wrong column, so it is copied to selected_category and cleared from
selected_business_type. Values that don't match a category name are left alone
— they are either already a genuine business type or stale junk, and in both
cases the 15-minute session TTL will clear them on the customer's next message.

Revision ID: 9f2c7ab41d63
Revises: c4d8a1f6e9b3
Create Date: 2026-08-24 08:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f2c7ab41d63'
down_revision: str | Sequence[str] | None = 'c4d8a1f6e9b3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'marketplace_sessions',
        sa.Column('selected_category', sa.String(length=100), nullable=True),
    )

    # Dedicated timestamp for the last_product_id freshness guard in
    # _resolve_photo_target. It previously read updated_at, which now gets
    # touched on every inbound message so the session TTL can measure real
    # inactivity — that would have left the guard permanently satisfied.
    op.add_column(
        'marketplace_sessions',
        sa.Column('last_product_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Seed it from updated_at for rows that already have a last_product_id, so
    # existing sessions get the old (approximate) behaviour on their next
    # message instead of losing the fallback outright.
    op.execute(
        """
        UPDATE marketplace_sessions
           SET last_product_at = updated_at
        WHERE last_product_id IS NOT NULL
          AND last_product_at IS NULL
        """
    )

    # Move category names that were living in selected_business_type into the
    # new column. Matched against categories.name globally rather than scoped
    # to selected_business_id, because a session sitting at the
    # 'select_business' step has the category set but no business chosen yet.
    op.execute(
        """
        UPDATE marketplace_sessions AS ms
           SET selected_category = ms.selected_business_type
        WHERE ms.selected_business_type IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM categories AS c
              WHERE c.name = ms.selected_business_type
          )
        """
    )

    # Only clear the old column where we actually copied the value out, so a
    # genuine business type is never destroyed.
    op.execute(
        """
        UPDATE marketplace_sessions AS ms
           SET selected_business_type = NULL
        WHERE ms.selected_category IS NOT NULL
          AND ms.selected_business_type = ms.selected_category
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Put the category back where the old code expects to find it, but only
    # for rows that don't already carry a business type — overwriting a real
    # business type would be worse than losing the category, which the session
    # TTL would have reset anyway.
    op.execute(
        """
        UPDATE marketplace_sessions AS ms
           SET selected_business_type = ms.selected_category
        WHERE ms.selected_category IS NOT NULL
          AND ms.selected_business_type IS NULL
        """
    )
    op.drop_column('marketplace_sessions', 'last_product_at')
    op.drop_column('marketplace_sessions', 'selected_category')
