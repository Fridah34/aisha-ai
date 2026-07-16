"""convert business_type to enum

Revision ID: 0642d5f701d1
Revises: d8fcf4e36829
Create Date: 2026-07-09 12:07:55.716541

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision= '0642d5f701d1'
down_revision  = 'd8fcf4e36829'
branch_labels = None
depends_on  = None

business_type_enum = sa.Enum(
    "retail", "fashion", "services", "food",
    name="businesstype"
)

def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: create the Postgres enum type itself
    business_type_enum.create(op.get_bind(), checkfirst=True)

    # Step 2: alter the column to use it, casting existing text values
    op.execute(
        "ALTER TABLE users "
        "ALTER COLUMN business_type TYPE businesstype "
        "USING business_type::businesstype"
    )

    # Step 3: enforce NOT NULL now that every row has a valid value
    op.alter_column("users", "business_type", nullable=False)



def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("users", "business_type", nullable=True)
    op.execute(
        "ALTER TABLE users "
        "ALTER COLUMN business_type TYPE VARCHAR(20) "
        "USING business_type:: text"
    )
    business_type_enum.drop(op.get_bind(), checkfirst=True)
