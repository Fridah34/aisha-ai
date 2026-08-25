# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

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

logger = logging.getLogger(__name__)

# Anchor all knowledge-base paths to this module's own location, not the
# process's current working directory. uvicorn and the RQ worker are separate
# OS processes and are not guaranteed to be launched from the same cwd — a
# bare relative path silently breaks depending on how/where each process is
# started. __file__ is stable regardless of launch context.
#
# BOTH directories are anchored to the BACKEND root so they resolve identically
# on a host checkout and inside the container. They must be: the Dockerfile
# builds with context ./backend into WORKDIR /app, which flattens backend/ to
# /app and drops the repo-root level entirely. Anchoring the system prompt at
# _REPO_ROOT therefore resolved to /knowledge_base/system_prompts/... in-container
# — a path that does not exist and is not even in the build context — so every
# customer message silently degraded to _FALLBACK_SYSTEM_PROMPT below.
#   <backend_root>/knowledge_base/system_prompts/aisha_voice.txt
#   <backend_root>/knowledge_base/clean_wiki/
# manager.py itself lives at <backend_root>/app/knowledge_base/manager.py
_MODULE_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _MODULE_DIR.parents[1]     # .../app/knowledge_base -> .../app -> .../backend
_REPO_ROOT = _MODULE_DIR.parents[2]        # .../app/knowledge_base -> .../app -> .../backend -> repo root

# Establish default global system tracking constraints paths
SYSTEM_PROMPT_PATH = _BACKEND_ROOT / "knowledge_base" / "system_prompts" / "aisha_voice.txt"
DEFAULT_CLEAN_WIKI_DIR = _BACKEND_ROOT / "knowledge_base" / "clean_wiki"

# Tried in order by _resolve_system_prompt_path(). The second entry is the
# pre-move repo-root location, kept so an older checkout or a deploy that still
# carries the file there is not silently downgraded to the fallback prompt.
_SYSTEM_PROMPT_CANDIDATES: tuple[Path, ...] = (
    SYSTEM_PROMPT_PATH,
    _REPO_ROOT / "knowledge_base" / "system_prompts" / "aisha_voice.txt",
)

# Escape hatch for deploys that mount the prompt somewhere else entirely
# (e.g. a Kubernetes ConfigMap or a secrets volume).
SYSTEM_PROMPT_PATH_ENV_VAR = "AISHA_SYSTEM_PROMPT_PATH"
DEFAULT_RETRIEVAL_LIMIT: int = 5
DEFAULT_CONVERSATION_LIMIT: int = 10

# Fallback used only if the system prompt file is missing, so a deploy/path
# mistake degrades to a generic-but-functional reply instead of silently
# killing every message job (see _load_system_block).
_FALLBACK_SYSTEM_PROMPT = (
    "You are AISHA, a helpful WhatsApp sales assistant. Answer customer "
    "questions about the store's products politely and concisely. If you "
    "are unsure of an answer, offer to connect the customer with a human."
)


class IngestionRejectedError(ValueError):
    """Triggered when an uploaded corporate asset fails raw regex safety checks."""



def _holds_prompt(path: Path) -> bool:
    """True only if `path` is a readable file with something actually in it."""
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _resolve_system_prompt_path() -> Path:
    """Returns the first candidate path that holds a non-empty prompt.

    Resolved per call rather than once at import time so a prompt file that is
    created or filled in after the process starts is picked up on the next
    message instead of needing a restart. When nothing is readable this returns
    SYSTEM_PROMPT_PATH so the resulting log line names the canonical location a
    developer should populate, rather than the last candidate tried.
    """
    override = os.getenv(SYSTEM_PROMPT_PATH_ENV_VAR)
    if override:
        # Returned unconditionally: an explicitly configured path that is
        # missing is a deploy error worth surfacing in the logs, not something
        # to paper over by quietly falling through to a bundled default.
        return Path(override).expanduser()

    for candidate in _SYSTEM_PROMPT_CANDIDATES:
        if _holds_prompt(candidate):
            return candidate

    return SYSTEM_PROMPT_PATH


# maxsize is >1 because the resolved path can differ between candidates and the
# env override. lru_cache does not cache exceptions, so the empty/missing case
# re-checks the disk on every call — which is what lets a file populated at
# runtime take effect without a restart.
@lru_cache(maxsize=4)
def _read_system_prompt(path: Path) -> str:
    """Reads the system prompt file from disk and caches the output in RAM."""
    if not path.is_file():
        raise FileNotFoundError(f"System prompt file missing at {path}")

    contents = path.read_text(encoding="utf-8").strip()

    # An empty file is a deploy mistake, not a valid "no persona" configuration,
    # so it gets the same loud fallback as a missing one. Previously this
    # returned "" and AISHA lost her entire persona and every response-tag
    # contract with nothing at all in the logs to explain why.
    if not contents:
        raise FileNotFoundError(f"System prompt file is empty at {path}")

    return contents


class KnowledgeBaseManager:
    """Manages secure, multi-tenant document ingestion, indexing, and prompt generation."""

    def __init__(
        self,
        session: AsyncSession,
        clean_wiki_dir: Path | str = DEFAULT_CLEAN_WIKI_DIR,
    ) -> None:
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
            raise FileNotFoundError(
                f"No such document for tenant {business_id}: {source_file}"
            )

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
            for row in existing_rows
            if hasattr(row, "section_path")
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
            if (
                existing is not None
                and getattr(existing, "content_hash", None) == content_hash
            ):
                result_rows.append(existing)
                continue

            # If raw data has changed, safely purge the old text slice to prevent orphan database entries
            if existing is not None:
                await self.session.delete(existing)

            # Format parent breadcrumb context directly inside body text for LLM visibility
            final_body = (
                f"Context: {chunk.section_path}\n\nData: {chunk.content}"
                if chunk.section_path
                else chunk.content
            )

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
        retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT,  # FIXED: Typo corrected (retrieval_limit)
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
        """Resolves system prompt blocks securely via our lru_cache file reader helper.

        Falls back to a generic in-code prompt if no candidate path holds a
        usable prompt, so a deploy/path misconfiguration degrades to a
        working-but-generic reply instead of silently failing every customer
        message job.
        """
        path = _resolve_system_prompt_path()
        try:
            return _read_system_prompt(path)
        except OSError as exc:  # FileNotFoundError, PermissionError, IsADirectoryError…
            logger.error(
                "%s — using fallback prompt, so AISHA has no persona and will not "
                "emit the [LANG:xx]/[HANDOVER_REQUIRED]/[SHOW_CATEGORIES] tags. "
                "Populate %s or set %s.",
                exc,
                SYSTEM_PROMPT_PATH,
                SYSTEM_PROMPT_PATH_ENV_VAR,
            )
            return _FALLBACK_SYSTEM_PROMPT

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
            AND search_vector @@ plainto_tsquery('simple', :query)
             ORDER BY ts_rank(search_vector, plainto_tsquery('simple', :query)) DESC
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

    async def _load_live_catalog_block(
        self, business_id: uuid.UUID
    ) -> list[ProductContext]:
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
                created_at=row.created_at,
            )
            for row in reversed(rows)
        ]
        
        