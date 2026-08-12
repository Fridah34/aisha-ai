"""add knowledge_documents table

Revision ID: b3f1c6a9d4e2
Revises: 8557c5fa405b
Create Date: 2026-07-20 06:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f1c6a9d4e2"
down_revision: str | Sequence[str] | None = "66ddb2c8ab4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

document_status_enum = sa.Enum(
    "learning", "ready", "failed", name="document_status"
)


def upgrade() -> None:
    """Upgrade schema."""
    # `document_status_enum` is created implicitly by `op.create_table` below
    # (Postgres has no `CREATE TYPE IF NOT EXISTS`, so it must only run once).
    op.create_table(
        "knowledge_documents",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "business_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stored_name", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            document_status_enum,
            nullable=False,
            server_default="learning",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String(50)), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "business_id", "stored_name", name="uq_knowledge_document_stored_name"
        ),
        sa.CheckConstraint(
            "char_length(display_name) > 0", name="chk_knowledge_document_name"
        ),
    )

    op.create_index(
        "ix_knowledge_documents_business_id", "knowledge_documents", ["business_id"]
    )
    op.create_index(
        "ix_knowledge_documents_created_at", "knowledge_documents", ["created_at"]
    )

    # update_updated_at_column() isn't defined anywhere earlier in this
    # migration chain (it was likely created manually, outside Alembic, on
    # whichever database this migration was originally authored against).
    # CREATE OR REPLACE makes this safe to run even if the function is
    # later added properly elsewhere — no duplicate-definition error.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER update_knowledge_documents_updated_at
        BEFORE UPDATE ON knowledge_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.execute("ALTER TABLE knowledge_documents ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE knowledge_documents FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_knowledge_documents ON knowledge_documents
        USING (business_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_knowledge_documents ON knowledge_documents;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS update_knowledge_documents_updated_at ON knowledge_documents;"
    )
    # Only drop the function if nothing else in the schema depends on it —
    # since this migration is what created it, it's the migration
    # responsible for cleaning it up on rollback.
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    op.drop_index("ix_knowledge_documents_created_at", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_business_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    document_status_enum.drop(op.get_bind(), checkfirst=True)
    
    