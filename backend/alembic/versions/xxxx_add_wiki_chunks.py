"""add wiki chunks and turn on rls

Revision ID: xxxx_add_wiki_chunks
"""
# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Replace 'xxxx_add_wiki_chunks' with your actual Alembic-generated revision UUID
revision = "xxxx_add_wiki_chunks"
down_revision = None  # Reference your previous baseline migration revision ID here
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates wiki_chunks table with constraints, indexes, automatic triggers, and RLS."""
    # Ensure UUID generation extension is active in the database
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 1. Create the physical multi-tenant wiki chunks table layout
    op.create_table(
        "wiki_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_file", sa.String(255), nullable=False),
        sa.Column("section_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        
        # Core Constraints
        sa.UniqueConstraint("business_id", "content_hash", name="uq_wiki_chunk_hash"),
        sa.CheckConstraint("char_length(chunk_text) > 0", name="chk_wiki_chunks_text_not_empty"),
        sa.CheckConstraint("content_hash <> ''", name="chk_wiki_chunks_hash_not_empty")
    )

    # 2. Inject the automated, self-generating Full-Text Search TSVector column
    op.execute(
        """
        ALTER TABLE wiki_chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED;
        """
    )

    # 3. Create high-speed indices
    # High-speed GIN index for full-text search vector queries
    op.create_index(
        "ix_wiki_chunks_search_vector",
        "wiki_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )
    # Single-column tenant index
    op.create_index("ix_wiki_chunks_business_id", "wiki_chunks", ["business_id"])
    
    # Composite tenant + file path index for document pruning, updates, and indexing lookups
    op.create_index(
        "ix_wiki_chunks_business_source",
        "wiki_chunks",
        ["business_id", "source_file"]
    )

    # 4. PostgreSQL Trigger to automatically update updated_at on modification
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
    )
    op.execute(
        """
        CREATE TRIGGER update_wiki_chunks_updated_at
        BEFORE UPDATE ON wiki_chunks
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # 5. Activate PostgreSQL Row-Level Security
    op.execute("ALTER TABLE wiki_chunks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE wiki_chunks FORCE ROW LEVEL SECURITY;")
    
    # 6. Establish multi-tenant isolation policy matching the manager session setting
    op.execute(
        """
        CREATE POLICY tenant_isolation_wiki_chunks ON wiki_chunks
        USING (business_id = current_setting('app.current_tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    """Safely tears down the table, its indexes, triggers, and policies."""
    # Drop RLS Policy
    op.execute("DROP POLICY IF EXISTS tenant_isolation_wiki_chunks ON wiki_chunks;")
    
    # Drop Automatic Timestamp Trigger
    op.execute("DROP TRIGGER IF EXISTS update_wiki_chunks_updated_at ON wiki_chunks;")
    
    # Explicitly drop custom-defined indexes
    op.drop_index("ix_wiki_chunks_business_source", table_name="wiki_chunks")
    op.drop_index("ix_wiki_chunks_business_id", table_name="wiki_chunks")
    op.drop_index("ix_wiki_chunks_search_vector", table_name="wiki_chunks")
    
    # Drop Table
    op.drop_table("wiki_chunks")