# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as EnumSQL,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


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
        CheckConstraint(
            "char_length(chunk_text) > 0", name="chk_wiki_chunks_text_not_empty"
        ),
        CheckConstraint("content_hash <> ''", name="chk_wiki_chunks_hash_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DocumentStatus(enum.Enum):
    """
    Business-facing document lifecycle. Deliberately hides implementation
    details (chunking/indexing/embeddings) behind plain-language states.
    """

    LEARNING = "learning"
    READY = "ready"
    FAILED = "failed"


class KnowledgeDocument(Base):
    """
    One row per document a business owner has uploaded to the Documents tab.

    This is distinct from `WikiChunk`: `WikiChunk` rows are the searchable
    text slices used for retrieval, while `KnowledgeDocument` is the
    business-facing record (name, size, status) shown in the document list.

    `stored_name` is the internal, collision-free filename used both as the
    physical filename on disk (under the tenant's `clean_wiki` folder and the
    raw-upload folder) and as the join key to `WikiChunk.source_file`. It is
    never shown to the business owner, who only ever sees `display_name`.
    """

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "stored_name", name="uq_knowledge_document_stored_name"
        ),
        CheckConstraint(
            "char_length(display_name) > 0", name="chk_knowledge_document_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        EnumSQL(DocumentStatus, name="document_status", values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
        default=DocumentStatus.LEARNING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(50)), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
