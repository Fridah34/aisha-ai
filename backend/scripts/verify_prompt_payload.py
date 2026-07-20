# Enable modern string-based type hinting
from __future__ import annotations

import asyncio
import time
import uuid

# Import active database session factory
from app.database import async_session_factory
from app.knowledge_base.chunking import normalize_query_for_retrieval
from app.knowledge_base.manager import KnowledgeBaseManager

# Localized multi-tenant testing variables using a valid v4 UUID
TEST_BUSINESS_ID = uuid.UUID("11111111-1111-4111-a111-111111111111")
TEST_MERCHANT_NAME = "Mama Njeri's Shop"

# Bilingual Kiswahili/English query
TEST_CUSTOMER_MESSAGE = "Je, mnasafirisha nje ya Nairobi kwa order ya 4k?"


async def run_prompt_pipeline_smoke_test() -> None:
    """Executes a live prompt rendering and verification simulation."""
    async with async_session_factory() as session:
        try:
            start_time = time.perf_counter()

            # Step 1: Initialize PostgreSQL Row-Level Security session context
            await KnowledgeBaseManager.set_tenant_context(session, TEST_BUSINESS_ID)
            manager = KnowledgeBaseManager(session)

            # Step 2: Assemble relational and vector text blocks into the payload
            payload = await manager.build_prompt_payload(
                business_id=TEST_BUSINESS_ID,
                merchant_name=TEST_MERCHANT_NAME,
                customer_message=TEST_CUSTOMER_MESSAGE,
            )

            # Step 3: Render the complete prompt string and verify security boundaries
            rendered = manager.render_and_verify(payload)

            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000

            # Step 4: Verify the payload actually contains our requested components
            assert TEST_MERCHANT_NAME in rendered, (
                "Merchant name missing from rendered prompt."
            )
            # The pipeline normalizes shorthand (e.g. "4k" -> "4000") before rendering,
            # so we assert against the normalized message rather than the raw literal.
            normalized_message = normalize_query_for_retrieval(TEST_CUSTOMER_MESSAGE)
            assert normalized_message in rendered, (
                "Customer message missing from rendered prompt."
            )
            # Verify structural prompt boundaries (adjust these if your template uses different headers)
            assert "SYSTEM" in rendered.upper() or "INSTRUCTION" in rendered.upper(), (
                "System rules missing."
            )

            # Step 5: Output clean, summarized diagnostic telemetry
            print("\nSUCCESS: PIPELINE EXECUTED CLEANLY")
            print("-" * 40)
            print(f"Merchant:         {TEST_MERCHANT_NAME}")
            print(f"Prompt Length:    {len(rendered)} characters")
            print(f"Approximate Tkns: {len(rendered) // 4}")
            print(f"Chunks Retrieved: {len(payload.retrieved_context)}")
            print(f"Execution Time:   {elapsed_ms:.0f} ms")
            print("-" * 40 + "\n")

        except ValueError as exc:
            # Catch known application-level validation errors separately
            print(f"PIPELINE REJECTED PAYLOAD: {exc}")
        except Exception as exc:
            # Catch and escalate unexpected crashes (e.g., DB connection drops)
            print(f"UNEXPECTED ERROR DURING RENDERING: {exc}")
            raise
        finally:
            # Step 6: Ensure the read-only transaction is cleanly rolled back
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(run_prompt_pipeline_smoke_test())
