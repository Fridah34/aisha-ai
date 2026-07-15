# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from app.knowledge_base.schemas import (
    ConversationTurn,
    Currency,
    ProductContext,
    RetrievedChunk,
)

# Generate two unguessable multi-tenant UUID markers for testing segregation
TENANT_A_ID = uuid.UUID("11111111-1111-4111-a111-111111111111")
TENANT_B_ID = uuid.UUID("22222222-2222-4222-b222-222222222222")


@pytest.fixture
def unit_mock_db_session() -> AsyncMock:
    """Spins up an asynchronous database connection mock context for pure unit tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.add = AsyncMock()
    return session


@pytest.fixture
def sample_retrieved_chunks() -> list[RetrievedChunk]:
    """Mock document text paragraph snippets."""
    return [
        RetrievedChunk(
            section_path="Shoes > Running",
            content="Our leather sports sneakers retail for KSh 3,500.",
            source_file="catalog.md"
        )
    ]


@pytest.fixture
def sample_products() -> list[ProductContext]:
    """Mock product catalog."""
    return [
        ProductContext(
            id=1,
            name="Suede Boots",
            price=Decimal("4500.00"),
            currency=Currency.KES,
            is_available=True,
            stock_quantity=12,
            sku="BOOT-001",
            description="Premium suede hiking boots."
        ),
        ProductContext(
            id=2,
            name="Red Satin Heels",
            price=Decimal("6000.00"),
            currency=Currency.KES,
            is_available=False,
            stock_quantity=0,
            sku="HEEL-001",
            description="Elegant red satin evening heels."
        )
    ]


@pytest.fixture
def sample_conversation_history() -> list[ConversationTurn]:
    """Mock conversation thread logs with locked timestamps."""
    return [
        ConversationTurn(
            role="user",
            content="Hello, do you have sneakers?",
            timestamp=datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
        ),
        ConversationTurn(
            role="assistant",
            content="Yes! Let me check our running shoes category.",
            timestamp=datetime(2026, 7, 14, 12, 0, 5, tzinfo=timezone.utc)
        )
    ]


@pytest.fixture
def sample_customer_message() -> str:
    """Mock customer query."""
    return "How much are the suede boots?"