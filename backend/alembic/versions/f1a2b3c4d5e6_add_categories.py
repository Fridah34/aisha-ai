
"""add categories table, product category_id, pending_action

Revision ID: f1a2b3c4d5e6
Revises: 664953c9f96f
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "664953c9f96f"
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT table_name FROM information_schema.tables WHERE table_name = :t"
    ), {"t": table})
    return result.first() is not None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table, "c": column})
    return result.first() is not None


def upgrade():
    conn = op.get_bind()

    if not _table_exists("categories"):
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("name", "user_id", name="uq_category_per_business"),
        )

    if not _column_exists("products", "category_id"):
        op.add_column("products", sa.Column("category_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_products_category_id", "products", "categories",
            ["category_id"], ["id"], ondelete="SET NULL"
        )

    if not _column_exists("conversation_states", "pending_action"):
        op.add_column(
            "conversation_states",
            sa.Column("pending_action", sa.String(50), nullable=True)
        )

    rows = conn.execute(sa.text(
        "SELECT DISTINCT user_id, category FROM products "
        "WHERE category IS NOT NULL AND category != ''"
    )).fetchall()

    for user_id, category_name in rows:
        existing = conn.execute(sa.text(
            "SELECT id FROM categories WHERE user_id = :u AND name = :n"
        ), {"u": user_id, "n": category_name}).first()

        if existing:
            category_id = existing[0]
        else:
            inserted = conn.execute(sa.text(
                "INSERT INTO categories (user_id, name, display_order, is_active) "
                "VALUES (:u, :n, 0, true) RETURNING id"
            ), {"u": user_id, "n": category_name})
            category_id = inserted.first()[0]

        conn.execute(sa.text(
            "UPDATE products SET category_id = :cid WHERE user_id = :u AND category = :n"
        ), {"cid": category_id, "u": user_id, "n": category_name})


def downgrade():
    if _column_exists("conversation_states", "pending_action"):
        op.drop_column("conversation_states", "pending_action")
    if _column_exists("products", "category_id"):
        op.drop_constraint("fk_products_category_id", "products", type_="foreignkey")
        op.drop_column("products", "category_id")
    if _table_exists("categories"):
        op.drop_table("categories")
