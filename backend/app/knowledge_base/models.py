# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import uuid
from datetime import datetime

from app.database import Base
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column


class WikiChunk(Base):
    """
    Multi-tenant, full-text-searchable knowledge base document chunk.

    Mirrors the `wiki_chunks` table created in the
    `xxxx_add_wiki_chunks` Alembic migration, including its Row-Level Security
    policy (`tenant_isolation_wiki_chunks`), which filters rows by
    `business_id = current_setting('app.current_tenant_id', true)::uuid`.
    """
    __tablename__ = "wiki_chunks"
    __table_args__ = (
        UniqueConstraint("business_id", "content_hash", name="uq_wiki_chunk_hash"),
        CheckConstraint("char_length(chunk_text) > 0", name="chk_wiki_chunks_text_not_empty"),
        CheckConstraint("content_hash <> ''", name="chk_wiki_chunks_hash_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    section_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Postgres `GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED` column.
    # Read-only from the ORM's perspective: never assign this attribute from Python,
    # the database computes and stores it automatically on every insert/update.
    # `server_default=FetchedValue()` tells SQLAlchemy this value is DB-generated,
    # so it's excluded from INSERT/UPDATE statements (required for GENERATED ALWAYS columns).
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, nullable=True, server_default=FetchedValue()
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


