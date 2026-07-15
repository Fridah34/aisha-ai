# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import hashlib
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Sequence

# Import custom hierarchical document slicing components
from app.knowledge_base.chunking import (
    chunk_markdown_document,
    normalize_query_for_retrieval,
)

# Import type-safe database mapping structure directly from models
from app.knowledge_base.models import WikiChunk

# Import network frontend input validator shapes
from app.knowledge_base.schemas import (
    ConversationTurn,
    ProductContext,
    PromptPayload,
    RetrievedChunk,
)

# Import bilingual multi-tenant input protection guardrails
from app.knowledge_base.security import (
    assert_no_embedded_secrets,
    flag_suspicious_upload,
    new_fence_tag,
    sanitize_untrusted_text,
)
from app.knowledge_base.tenancy import TenantFileResolver
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Establish default global system tracking constraints paths
SYSTEM_PROMPT_PATH = Path("knowledge_base/system_prompts/aisha_voice.txt")
DEFAULT_RETRIEVAL_LIMIT: int = 5
DEFAULT_CONVERSATION_LIMIT: int = 10


class IngestionRejectedError(ValueError):
    """Triggered when an uploaded corporate asset fails raw regex safety checks."""
    pass


@lru_cache(maxsize=1)
def _read_system_prompt(path: Path) -> str:
    """Reads the system prompt file from disk and caches the output in RAM."""
    if not path.is_file():
        raise FileNotFoundError(f"System prompt file missing at {path}")
    return path.read_text(encoding="utf-8").strip()


class KnowledgeBaseManager:
    """Manages secure, multi-tenant document ingestion, indexing, and prompt generation."""

    def __init__(self, session: AsyncSession, clean_wiki_dir: Path | str = "knowledge_base/clean_wiki") -> None:
        self.session: AsyncSession = session
        # Lock down our directory traversal sandbox safety resolver
        self.resolver: TenantFileResolver = TenantFileResolver(base_dir=clean_wiki_dir)

    @staticmethod
    async def set_tenant_context(session: AsyncSession, business_id: uuid.UUID) -> None:
        """Sets the active connection setting context to trigger PostgreSQL Row-Level Security."""
        try:
            parsed = uuid.UUID(str(business_id))
        except (ValueError, AttributeError, TypeError):
            raise ValueError(f"Invalid tenant id for RLS context: {business_id!r}")
        
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :business_id, true)"),
            {"business_id": str(parsed)},
        )

    async def ingest_document(
        self,
        business_id: uuid.UUID,
        source_file: str,
        allow_suspicious: bool = False,
    ) -> list[WikiChunk]:
        """Orchestrates an idempotent background documentation data load into Postgres."""
        # Step 0: Initialize PostgreSQL Row-Level Security for this active database session
        await self.set_tenant_context(self.session, business_id)

        # Step 1: Secure and resolve path boundaries entirely in RAM memory first
        file_path = self.resolver.resolve_within_tenant(business_id, source_file)
        if not file_path.is_file():
            raise FileNotFoundError(f"No such document for tenant {business_id}: {source_file}")

        raw_text = file_path.read_text(encoding="utf-8")

        # Step 2: Screen text data layers for malicious prompt injections
        suspicious_hits = flag_suspicious_upload(raw_text)
        if suspicious_hits and not allow_suspicious:
            raise IngestionRejectedError(
                f"Document {source_file} flagged for suspicious content "
                f"({len(suspicious_hits)} pattern match(es)); not indexed."
            )

        # Step 3: Run hierarchical text slicing on markdown headers
        chunks = chunk_markdown_document(raw_text)

        # Step 4: Fetch existing rows to evaluate content hashes
        existing_rows_seq = await self.session.execute(
            select(WikiChunk).where(
                WikiChunk.business_id == business_id,
                WikiChunk.source_file == source_file,
            )
        )
        existing_rows: Sequence[WikiChunk] = existing_rows_seq.scalars().all()
        
        # Map existing rows via section_path instead of db-generated auto-incrementing ID
        existing_by_section: dict[str, WikiChunk] = {
            f"{row.source_file}#{row.section_path}": row 
            for row in existing_rows if hasattr(row, "section_path")
        }

        # Fallback dictionary mapping: If schema does not use section_path columns, fallback to text content hashing
        if not existing_by_section:
            existing_by_section = {
                f"{row.source_file}#{hashlib.sha256(row.chunk_text.encode('utf-8')).hexdigest()}": row
                for row in existing_rows
            }

        seen_chunks: set[str] = set()
        result_rows: list[WikiChunk] = []

        # Step 5: Run idempotency check loops across chunks
        for chunk in chunks:
            # REPLACED: md5 hash changed to secure sha256 content hashing
            content_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
            
            # Form consistent compound key checking strings
            chunk_key = f"{source_file}#{chunk.section_path}"
            seen_chunks.add(chunk_key)
            
            existing = existing_by_section.get(chunk_key)

            # If the exact text paragraph and path match signature exactly, skip database writes
            if existing is not None and getattr(existing, "content_hash", None) == content_hash:
                result_rows.append(existing)
                continue

            # If raw data has changed, safely purge the old text slice to prevent orphan database entries
            if existing is not None:
                await self.session.delete(existing)

            # Format parent breadcrumb context directly inside body text for LLM visibility
            final_body = f"Context: {chunk.section_path}\n\nData: {chunk.content}" if chunk.section_path else chunk.content
            
            # Instantiate clean updated text snippet row representation
            new_row = WikiChunk(
                business_id=business_id,
                source_file=source_file,
                chunk_text=final_body,
                section_path=chunk.section_path,
                content_hash=content_hash,
            )
            
            self.session.add(new_row)
            result_rows.append(new_row)

        # Step 6: Prune any old dead sections that were completely removed from the markdown file
        for key, row in existing_by_section.items():
            if key not in seen_chunks:
                await self.session.delete(row)

        await self.session.flush()
        return result_rows

    async def build_prompt_payload(
        self,
        business_id: uuid.UUID,
        merchant_name: str,
        customer_message: str,
        retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT,  # FIXED: Typo corrected (retretrieval_limit)
        conversation_limit: int = DEFAULT_CONVERSATION_LIMIT,
    ) -> PromptPayload:
        """Assembles unified, secure context bundles on-the-fly during customer WhatsApp chats."""
        # 0. Set connection variable Context for Postgres Row-Level Security validation rules
        await self.set_tenant_context(self.session, business_id)

        # 1. Standardize numerical shorthands like '1.5k' into '1500' in RAM memory
        normalized_message = normalize_query_for_retrieval(customer_message)
        sanitized_message = sanitize_untrusted_text(normalized_message)

        # 2. Compile foundational system rules files data (Loaded via Cached method)
        system_block = self._load_system_block()
        
        # 3. Pull matching facts via fast GIN Inverted Text Index scans
        retrieved_context = await self._load_retrieved_context_block(
            business_id, sanitized_message, limit=retrieval_limit
        )
        
        # 4. Pull live transactional inventory status strings from Postgres database rows
        live_catalog = await self._load_live_catalog_block(business_id)
        
        # 5. Extract conversation log histories, sorted beautifully from oldest to newest
        recent_conversation = await self._load_conversation_block(
            business_id, limit=conversation_limit
        )

        # 6. Bundle components inside our secure, self-defending prompt envelope shape
        return PromptPayload(
            system_block=system_block,
            merchant_name=merchant_name,
            fence_tag=new_fence_tag(),
            retrieved_context=retrieved_context,
            live_catalog=live_catalog,
            recent_conversation=recent_conversation,
            customer_message=sanitized_message,
        )

    def render_and_verify(self, payload: PromptPayload) -> str:
        """Renders prompt layout frames and shields against production credential key leaks."""
        rendered = payload.render()
        assert_no_embedded_secrets(rendered)
        return rendered

    def _load_system_block(self) -> str:
        """Resolves system prompt blocks securely via our lru_cache file reader helper."""
        #  CACHED: Using lru_cache wrapper to prevent redundant file system disk reading
        return _read_system_prompt(SYSTEM_PROMPT_PATH)

    async def _load_retrieved_context_block(
        self, business_id: uuid.UUID, query: str, limit: int
    ) -> list[RetrievedChunk]:
        """Queries database wiki chunks returning actual section path fields."""
        # RESOLVED: Retrieving original section_path from database rows 
        sql = text(
            """
            SELECT source_file, chunk_text, section_path
            FROM wiki_chunks
            WHERE business_id = :business_id
              AND to_tsvector('simple', chunk_text) @@ plainto_tsquery('simple', :query)
            ORDER BY ts_rank(to_tsvector('simple', chunk_text), plainto_tsquery('simple', :query)) DESC
            LIMIT :limit
            """
        )
        result = await self.session.execute(
            sql, {"business_id": str(business_id), "query": query, "limit": limit}
        )
        rows = result.mappings().all()

        return [
            RetrievedChunk(
                section_path=row["section_path"] or "",
                content=row["chunk_text"],
                source_file=row["source_file"],
            )
            for row in rows
        ]

    async def _load_live_catalog_block(self, business_id: uuid.UUID) -> list[ProductContext]:
        """Fetches all inventory products ensuring consistency with active catalog rendering."""
        # Connects smoothly to your optimized SQLAlchemy 2.0 Product table class schema
        from app.models import Product

        # CONSISTENCY: Loads both available and out-of-stock items to match catalog split rendering logic
        result = await self.session.execute(
            select(Product).where(Product.business_id == business_id)
        )
        rows = result.scalars().all()

        return [ProductContext.model_validate(p) for p in rows]

    async def _load_conversation_block(
        self, business_id: uuid.UUID, limit: int
    ) -> list[ConversationTurn]:
        """Resolves database conversation history preserving created_at timestamps."""
        # Connects smoothly to your type-safe ChatMessage model table setup
        from app.models import ChatMessage
        
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.business_id == business_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        
        #  PRESERVED: Timestamps mapped explicitly from Database Row created_at fields
        return [
            ConversationTurn(
                role=row.role,
                content=row.content,
                timestamp=row.created_at,
            )
            for row in reversed(rows)
        ]