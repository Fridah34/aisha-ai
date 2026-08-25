"""restore knowledge_documents and wiki_chunks tables

Revision ID: c4d8a1f6e9b3
Revises: f7a3c9d21b48
Create Date: 2026-07-30 12:00:00.000000

`0e0d0ac930b0_add_last_product_id_to_marketplace_.py` was generated with
`alembic revision --autogenerate` while `Base.metadata` didn't have
`app.knowledge_base.models` imported. Autogenerate diffed the live DB
against that incomplete metadata, concluded `wiki_chunks` and
`knowledge_documents` were "extra" tables, and silently emitted
`op.drop_table(...)` for both inside what was meant to be a migration that
only adds `marketplace_sessions.last_product_id`. That migration is already
applied (this repo's current head descends from it), so both tables are
gone from the database even though the ORM models, RLS policies, and
application code (`app/knowledge_base/`) still expect them.

This migration recreates both tables to match the current ORM models in
`app/knowledge_base/models.py` exactly (including Row-Level Security and
the `search_vector` generated column), rather than reverting via
`0e0d0ac930b0`'s downgrade(), because that auto-generated downgrade only
captures raw column/table DDL - it does not restore the RLS policies, the
`updated_at` trigger, or the `GENERATED ALWAYS ... STORED` expression on
`wiki_chunks.search_vector`.

`0e0d0ac930b0` dropped the tables but never dropped the `document_status`
enum type or the `update_updated_at_column()` trigger function (Postgres
only cascades trigger/policy/index drops that belong to the dropped
table, not free-standing types/functions), so both are handled
idempotently below.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8a1f6e9b3"
down_revision: str | Sequence[str] | None = "f7a3c9d21b48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

document_status_enum = sa.Enum("learning", "ready", "failed", name="document_status")


def upgrade() -> None:
    """Upgrade schema."""
    # The enum type was never dropped when the table was dropped (Postgres
    # has no `CREATE TYPE IF NOT EXISTS`, and `op.create_table` below always
    # re-emits `CREATE TYPE`), so drop it first to avoid `DuplicateObject`.
    op.execute("DROP TYPE IF EXISTS document_status;")

    # --- knowledge_documents ---
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

    # Idempotent: this function is independent of the table and may still
    # exist from before the table was dropped.
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

    # --- wiki_chunks ---
    op.create_table(
        "wiki_chunks",
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
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("section_path", sa.String(500), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        # Matches app/knowledge_base/models.py's WikiChunk.search_vector:
        # a Postgres GENERATED ALWAYS ... STORED column, computed by the
        # database on every insert/update - never written by the ORM.
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', chunk_text)", persisted=True),
            nullable=True,
        ),
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
        sa.UniqueConstraint("business_id", "content_hash", name="uq_wiki_chunk_hash"),
        sa.CheckConstraint(
            "char_length(chunk_text) > 0", name="chk_wiki_chunks_text_not_empty"
        ),
        sa.CheckConstraint("content_hash <> ''", name="chk_wiki_chunks_hash_not_empty"),
    )

    op.create_index("ix_wiki_chunks_business_id", "wiki_chunks", ["business_id"])
    op.create_index("ix_wiki_chunks_created_at", "wiki_chunks", ["created_at"])

    op.execute(
        """
        CREATE TRIGGER update_wiki_chunks_updated_at
        BEFORE UPDATE ON wiki_chunks
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.execute("ALTER TABLE wiki_chunks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE wiki_chunks FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_wiki_chunks ON wiki_chunks
        USING (business_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation_wiki_chunks ON wiki_chunks;")
    op.execute("DROP TRIGGER IF EXISTS update_wiki_chunks_updated_at ON wiki_chunks;")
    op.drop_index("ix_wiki_chunks_created_at", table_name="wiki_chunks")
    op.drop_index("ix_wiki_chunks_business_id", table_name="wiki_chunks")
    op.drop_table("wiki_chunks")

    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_knowledge_documents ON knowledge_documents;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS update_knowledge_documents_updated_at ON knowledge_documents;"
    )
    op.drop_index("ix_knowledge_documents_created_at", table_name="knowledge_documents")
    op.drop_index(
        "ix_knowledge_documents_business_id", table_name="knowledge_documents"
    )
    op.drop_table("knowledge_documents")
    document_status_enum.drop(op.get_bind(), checkfirst=True)
