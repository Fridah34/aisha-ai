"""SQLAlchemy ORM models for the AISHA multi-tenant persistence layer.

Every primary and foreign key is a native PostgreSQL UUID. Row-Level Security (RLS)
policies enforced at the database layer key off the `business_id` column present on
every tenant-scoped table, so that column's name and type (`UUID(as_uuid=True)`) must
never drift, or `current_setting('app.current_tenant_id', true)::uuid` comparisons in
RLS policies will break.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal  # Guarding against floating-point transaction errors

from app.database import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


# ==============================================================================
# ENUMS
# ==============================================================================
class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class MessageRole(enum.Enum):
    """Who authored a given `Conversation` message."""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    HUMAN = "HUMAN"


class Language(enum.Enum):
    """Supported customer-facing conversation languages. EN = English, SW = Swahili."""
    EN = "EN"
    SW = "SW"


class HandoverStatus(enum.Enum):
    AI_ACTIVE = "AI_ACTIVE"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    RESOLVED = "RESOLVED"


# ==============================================================================
# USER (TENANT / MERCHANT ACCOUNT)
# ==============================================================================
class User(Base):
    """The master account identity table for registered retail shop merchants (tenants)."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    knowledge_base_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(20), default="retail", nullable=True)
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    whatsapp_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # server_default=func.now() means PostgreSQL sets this automatically.
    # More reliable than setting it in Python because it uses the
    # database server's clock, not the application host's clock.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    products: Mapped[list["Product"]] = relationship("Product", back_populates="business")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="business")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="business")
    conversation_states: Mapped[list["ConversationState"]] = relationship(
        "ConversationState", back_populates="business"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="business")


# ==============================================================================
# PRODUCT
# ==============================================================================
class Product(Base):
    """The physical transactional product catalog inventory tracking layer."""
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variant_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    variant_options: Mapped[str | None] = mapped_column(String(300), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    upsell_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped["User"] = relationship("User", back_populates="products")
    order_items: Mapped[list["Order"]] = relationship("Order", back_populates="product")  # <-- MUST BE SINGULAR


# ==============================================================================
# CUSTOMER
# ==============================================================================
class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="customer")
    conversation_states: Mapped[list["ConversationState"]] = relationship(
        "ConversationState", back_populates="customer"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")


# ==============================================================================
# CONVERSATION (CUSTOMER-FACING WHATSAPP AUDIT / HANDOVER LOG)
# ==============================================================================
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[MessageRole] = mapped_column(EnumSQL(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Language] = mapped_column(EnumSQL(Language), default=Language.EN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivery_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="conversations")
    business: Mapped["User"] = relationship("User", back_populates="conversations")


# ==============================================================================
# CONVERSATION STATE (AI <-> HUMAN HANDOVER TRACKING)
# ==============================================================================
class ConversationState(Base):
    __tablename__ = "conversation_states"
    __table_args__ = (
        UniqueConstraint("customer_id", "business_id", name="uq_customer_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[HandoverStatus] = mapped_column(
        EnumSQL(HandoverStatus), default=HandoverStatus.AI_ACTIVE, nullable=False
    )
    taken_over_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="conversation_states")
    business: Mapped["User"] = relationship("User", back_populates="conversation_states")


# ==============================================================================
# ORDER
# ==============================================================================
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(EnumSQL(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    snapshot_customer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_customer_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_product_name: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_product_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    snapshot_business_name: Mapped[str | None] = mapped_column(String, nullable=True)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")
    business: Mapped["User"] = relationship("User", back_populates="orders")


# ==============================================================================
# CHAT MESSAGE (AI PROMPT-CONTEXT SESSION LOG — MARKETPLACE HUB AWARE)
# ==============================================================================
class ChatMessage(Base):
    """
    Multi-tenant AI conversation session log used to build LLM prompt context windows
    (see `KnowledgeBaseManager._load_conversation_block`). Distinct from `Conversation`,
    which is the customer-facing WhatsApp audit/handover log.
    """
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Groups chat log rows into a single conversational thread/session.
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, nullable=False, index=True
    )

    # Marketplace Hub routing metadata: tracks whether this message was forwarded to
    # another tenant's storefront (`active_tenant_id`) instead of handled directly.
    active_tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    routing_state: Mapped[str] = mapped_column(String, default="DIRECT", nullable=False)  # 'DIRECT' vs 'FORWARDED'

    role: Mapped[str] = mapped_column(String, nullable=False)  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    business: Mapped["User"] = relationship("User", back_populates="chat_messages")