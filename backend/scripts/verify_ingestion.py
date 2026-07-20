# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import asyncio
import tempfile
import uuid
from pathlib import Path

# Import our active app connection session factories
from app.database import async_session_factory
from app.knowledge_base.manager import IngestionRejectedError, KnowledgeBaseManager

# Register all SQLAlchemy models on the shared Base metadata (mirrors main.py)
# so cross-model foreign keys, like wiki_chunks -> users, can be resolved.
from app.models import User

# Seed our locked conftest test tracking profile identifier signature
TEST_BUSINESS_ID = uuid.UUID("11111111-1111-4111-a111-111111111111")
TEST_SOURCE_FILE = "policy.md"

SAMPLE_MARKDOWN = """\
## Shipping

We ship within Nairobi in 1-2 days. Shipping cost is 200 KES for orders under 4000.
Orders above 4000 ship free within Nairobi.

### International

We do not currently ship outside Kenya.

## Returns

Items can be returned within 7 days if unused and in original packaging.
"""


async def run_ingestion_smoke_test() -> None:
    """Executes a live, self-cleaning background parsing and ingestion data load simulation."""

    # Isolate filesystem writes to prevent polluting development data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        async with async_session_factory() as session:
            # Step 1: Initialize PostgreSQL Row-Level Security connection settings context
            await KnowledgeBaseManager.set_tenant_context(session, TEST_BUSINESS_ID)

            # Seed a temporary tenant/user row so wiki_chunks.business_id's FK constraint
            # is satisfied. Rolled back at the end alongside the ingested chunks.
            session.add(
                User(
                    id=TEST_BUSINESS_ID,
                    name="Smoke Test Tenant",
                    email="smoke-test@example.com",
                    business_name="Smoke Test Business",
                )
            )
            await session.flush()

            # Initialize manager and override its storage path to use our temporary sandbox
            manager = KnowledgeBaseManager(session, clean_wiki_dir=temp_path)

            # Step 2: Provision the sandboxed physical folder directories on disk
            tenant_dir = manager.resolver.ensure_tenant_root(TEST_BUSINESS_ID)
            (tenant_dir / TEST_SOURCE_FILE).write_text(
                SAMPLE_MARKDOWN, encoding="utf-8"
            )

            # Step 3: Trigger the idempotent ingestion pipeline inside a safe transaction
            try:
                chunks = await manager.ingest_document(
                    TEST_BUSINESS_ID, TEST_SOURCE_FILE
                )

                # Step 4: Verify the indexed chunks (True Verification)
                assert len(chunks) >= 2, (
                    "Failed to generate multiple chunks from markdown."
                )
                assert any("Shipping" in chunk.chunk_text for chunk in chunks), (
                    "Missing Shipping section."
                )
                assert any("Returns" in chunk.chunk_text for chunk in chunks), (
                    "Missing Returns section."
                )

                # Step 5: Print clean diagnostic telemetry metrics to the terminal
                print(
                    f"SUCCESS: Indexed {len(chunks)} chunk(s) for tenant {TEST_BUSINESS_ID}:\n"
                )
                for chunk in chunks:
                    print(
                        f"File: {chunk.source_file} | Path: {getattr(chunk, 'section_path', 'N/A')}"
                    )
                    print(
                        f"Text: {chunk.chunk_text[:120].replace('\n', ' ')}{'...' if len(chunk.chunk_text) > 120 else ''}"
                    )
                    print("-" * 50)

            except IngestionRejectedError as exc:
                print(f"INGESTION REJECTED BY SECURITY SUITE: {exc}")
            except Exception as exc:
                print(f"UNEXPECTED ERROR DURING INGESTION: {exc}")
                raise
            finally:
                # Step 6: Roll back instead of committing to keep the database pristine
                await session.rollback()
                print("Transaction rolled back successfully. Database remains clean.")


if __name__ == "__main__":
    asyncio.run(run_ingestion_smoke_test())
