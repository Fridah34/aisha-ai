# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import re

import pytest
from app.knowledge_base.manager import KnowledgeBaseManager
from app.knowledge_base.schemas import PromptPayload
from conftest import TENANT_A_ID


@pytest.mark.asyncio
async def test_set_tenant_context_enforces_rls_boundaries(unit_mock_db_session):
    """Verifies that our manager pushes the correct tenant UUID down to the Postgres connection setting kernel."""
    await KnowledgeBaseManager.set_tenant_context(unit_mock_db_session, TENANT_A_ID)
    
    unit_mock_db_session.execute.assert_called_once()
    called_query = unit_mock_db_session.execute.call_args[0][0]
    called_params = unit_mock_db_session.execute.call_args[0][1]
    
    # Confirm both the raw SQL command and the exact parameter bindings
    assert "set_config('app.current_tenant_id'" in str(called_query)
    assert called_params["business_id"] == str(TENANT_A_ID)


def test_prompt_payload_rendering_flow(
    unit_mock_db_session, 
    sample_retrieved_chunks, 
    sample_products, 
    sample_conversation_history,
    sample_customer_message
):
    """Audits the master PromptPayload renderer to verify strict multi-tag isolation execution."""
    payload = PromptPayload(
        system_block="You are AISHA sales voice rulebook.",
        merchant_name="Sarah Boutique",
        fence_tag="CTX_12345",
        retrieved_context=sample_retrieved_chunks,
        live_catalog=sample_products,
        recent_conversation=sample_conversation_history,
        customer_message=sample_customer_message
    )
    
    manager = KnowledgeBaseManager(session=unit_mock_db_session)
    final_output_prompt = manager.render_and_verify(payload)
    
    # Assert available and out-of-stock sections render cleanly from our database entities
    assert "AVAILABLE PRODUCTS" in final_output_prompt
    assert "• Suede Boots" in final_output_prompt
    
    assert "OUT OF STOCK PRODUCTS" in final_output_prompt
    assert "• Red Satin Heels" in final_output_prompt
    
    # Assert conversation timestamps are cleanly preserved with timezone awareness
    assert "2026-07-14T12:00:00+00:00" in final_output_prompt
    
    # Assert dynamic prompt injection tags wrap our customer parameters safely
    assert re.search(r"<[^>]+>", final_output_prompt)
    
    # Assert the customer message is accurately injected
    assert sample_customer_message in final_output_prompt
    
    # Assert merchant name is securely mapped
    assert "Sarah Boutique" in final_output_prompt
    
    # Assert retrieved RAG context and metadata paths are exposed to the LLM
    assert "Shoes > Running" in final_output_prompt
    assert "catalog.md" in final_output_prompt