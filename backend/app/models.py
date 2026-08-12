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
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ==============================================================================
# ENUMS
# ==============================================================================
class OrderStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class MessageRole(enum.Enum):
    """Who authored a given `Conversation` or `ChatMessage` log."""

    Customer = "Customer"
    Assistant = "Assistant"
    Human = "Human"


class Language(enum.Enum):
    """Supported conversation languages. en = English, sw = Swahili"""

    en = "en"
    sw = "sw"


class HandoverStatus(enum.Enum):
    AI_ACTIVE = "AI_ACTIVE"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    RESOLVED = "RESOLVED"


class HandoverEventStatus(enum.Enum):
    """Lifecycle of a single `HandoverEvent` audit row — distinct from the
    live per-customer `HandoverStatus` above. New statuses can be appended
    here without touching the notification engine."""

    WAITING = "WAITING"
    ACCEPTED = "ACCEPTED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class HandoverReasonCode(enum.Enum):
    """Machine-readable reason a conversation was escalated to a human.
    The frontend maps each code to a human-readable label
    (see app/handover/reason_codes.py) — never display the raw code."""

    CUSTOMER_REQUESTED_HUMAN = "CUSTOMER_REQUESTED_HUMAN"
    DISCOUNT_NEGOTIATION = "DISCOUNT_NEGOTIATION"
    BULK_ORDER = "BULK_ORDER"
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    ORDER_DISPUTE = "ORDER_DISPUTE"
    COMPLAINT = "COMPLAINT"
    REFUND_REQUEST = "REFUND_REQUEST"
    DAMAGED_PRODUCT = "DAMAGED_PRODUCT"
    CUSTOM_ORDER = "CUSTOM_ORDER"
    ACCOUNT_ACCESS_REQUIRED = "ACCOUNT_ACCESS_REQUIRED"
    BUSINESS_RULE_TRIGGERED = "BUSINESS_RULE_TRIGGERED"


# Default per-channel notification configuration — used both as the ORM
# column default (new rows) and as the merge-in fallback anywhere
# `User.handover_notifications` might be missing a channel (e.g. rows
# written before a new channel key existed). Single source of truth so the
# API layer and the notification engine can never disagree on defaults.
DEFAULT_HANDOVER_NOTIFICATIONS: dict[str, dict[str, Any]] = {
    "dashboard": {"enabled": True, "delay_minutes": 0},
    "whatsapp": {"enabled": True, "delay_minutes": 0},
    "email": {"enabled": True, "delay_minutes": 5},
}


class BusinessType(enum.Enum):
    retail = "retail"
    fashion = "fashion"
    services = "services"
    food = "food"


# ==============================================================================
# USER (TENANT / MERCHANT ACCOUNT)
# ==============================================================================
class User(Base):
    """The master account identity table for registered retail shop merchants (tenants)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    business_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    knowledge_base_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    business_type: Mapped[BusinessType] = mapped_column(
        EnumSQL(BusinessType), default=BusinessType.retail, nullable=False
    )
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    whatsapp_phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    handover_notifications: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: DEFAULT_HANDOVER_NOTIFICATIONS,
        server_default=text(
            "'{\"dashboard\": {\"enabled\": true, \"delay_minutes\": 0}, "
            "\"whatsapp\": {\"enabled\": true, \"delay_minutes\": 0}, "
            "\"email\": {\"enabled\": true, \"delay_minutes\": 5}}'::json"
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Direct ownership relationships backed by unit tracking lifecycle cascades
    products: Mapped[list[Product]] = relationship(
        "Product", back_populates="business", cascade="all, delete-orphan"
    )
    categories: Mapped[list[Category]] = relationship(
        "Category", back_populates="business", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(
        "Order", back_populates="business"
    )  # Protected via SET NULL behavior
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="business", cascade="all, delete-orphan"
    )
    conversation_states: Mapped[list[ConversationState]] = relationship(
        "ConversationState",
        back_populates="business",
        foreign_keys="ConversationState.business_id",
        cascade="all, delete-orphan",
    )
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="business", cascade="all, delete-orphan"
    )
    customers: Mapped[list[Customer]] = relationship(
        "Customer", back_populates="business", cascade="all, delete-orphan"
    )
    carts: Mapped[list[Cart]] = relationship(
        "Cart", back_populates="business", cascade="all, delete-orphan"
    )
    handover_events: Mapped[list[HandoverEvent]] = relationship(
        "HandoverEvent", back_populates="business", cascade="all, delete-orphan"
    )
    # Reverse reference lookups handled safely via viewonly boundaries
    selected_conversation_states: Mapped[list[ConversationState]] = relationship(
        "ConversationState",
        foreign_keys="ConversationState.selected_business_id",
        viewonly=True,
    )
    marketplace_sessions: Mapped[list[MarketplaceSession]] = relationship(
        "MarketplaceSession",
        foreign_keys="MarketplaceSession.selected_business_id",
        viewonly=True,
    )


# ==============================================================================
# CATEGORY
# ==============================================================================
class Category(Base):
    """New entity grouping products per business branch."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", "business_id", name="uq_category_per_business"),
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

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    business: Mapped[User] = relationship("User", back_populates="categories")
    products: Mapped[list[Product]] = relationship(
        "Product", back_populates="category"
    )

    # Reverse tracking for marketplace navigation metrics
    conversation_states: Mapped[list[ConversationState]] = relationship(
        "ConversationState",
        foreign_keys="ConversationState.selected_category_id",
        viewonly=True,
    )


# ==============================================================================
# PRODUCT
# ==============================================================================
class Product(Base):
    """The physical transactional product catalog inventory tracking layer."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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
    variant_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    variant_options: Mapped[str | None] = mapped_column(String(300), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    upsell_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped[User] = relationship("User", back_populates="products")
    category: Mapped[Category] = relationship("Category", back_populates="products")
    orders: Mapped[list[Order]] = relationship("Order", back_populates="product")

    # Reverse tracking helper for analytics pipelines
    marketplace_sessions: Mapped[list[MarketplaceSession]] = relationship(
        "MarketplaceSession",
        foreign_keys="MarketplaceSession.selected_product_id",
        viewonly=True,
    )

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None


# ==============================================================================
# CUSTOMER
# ==============================================================================
class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint(
            "phone_number", "business_id", name="uq_customer_per_business"
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
    phone_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="customer"
    )
    conversation_states: Mapped[list[ConversationState]] = relationship(
        "ConversationState", back_populates="customer"
    )
    handover_events: Mapped[list[HandoverEvent]] = relationship(
        "HandoverEvent", back_populates="customer", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship("Order", back_populates="customer")
    business: Mapped[User] = relationship("User", back_populates="customers")


# ==============================================================================
# CONVERSATION
# ==============================================================================
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[MessageRole] = mapped_column(EnumSQL(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Language] = mapped_column(
        EnumSQL(Language), default=Language.en, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    delivery_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="conversations"
    )
    business: Mapped[User] = relationship("User", back_populates="conversations")


# ==============================================================================
# CONVERSATION STATE
# ==============================================================================
class ConversationState(Base):
    __tablename__ = "conversation_states"
    __table_args__ = (
        UniqueConstraint("customer_id", "business_id", name="uq_customer_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[HandoverStatus] = mapped_column(
        EnumSQL(HandoverStatus), default=HandoverStatus.AI_ACTIVE, nullable=False
    )
    pending_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    taken_over_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Marketplace routing integrations
    selected_business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    selected_business_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    selected_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    customer: Mapped[Customer] = relationship(
        "Customer", back_populates="conversation_states"
    )
    business: Mapped[User] = relationship(
        "User", back_populates="conversation_states", foreign_keys=[business_id]
    )
    selected_business: Mapped[User | None] = relationship(
        "User", foreign_keys=[selected_business_id]
    )
    selected_category: Mapped[Category | None] = relationship(
        "Category", foreign_keys=[selected_category_id]
    )


# ==============================================================================
# MARKETPLACE SESSION
# ==============================================================================
class MarketplaceSession(Base):
    """Tracks generic temporary customer navigation states across WhatsApp stores."""

    __tablename__ = "marketplace_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    pending_action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    selected_business_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    selected_business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    last_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    last_product: Mapped[Product | None] = relationship(
        "Product", foreign_keys= [last_product_id]
    )
    
    
    selected_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    selected_size: Mapped[str | None] = mapped_column(String(20), nullable=True)

    list_offset: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )

    # ORM Navigation Helpers
    selected_business: Mapped[User | None] = relationship(
        "User", foreign_keys=[selected_business_id]
    )
    selected_product: Mapped[Product | None] = relationship(
        "Product", foreign_keys=[selected_product_id]
    )


# ==============================================================================
# CART
# ==============================================================================
class Cart(Base):
    """Persistent shopping carts structured to save item listings via JSON."""

    __tablename__ = "carts"
    __table_args__ = (
        UniqueConstraint("phone_number", "business_id", name="uq_cart_per_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped[User] = relationship("User", back_populates="carts")


# ==============================================================================
# ORDER
# ==============================================================================
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        EnumSQL(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    snapshot_customer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_customer_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_product_name: Mapped[str | None] = mapped_column(String, nullable=True)
    snapshot_product_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    snapshot_business_name: Mapped[str | None] = mapped_column(String, nullable=True)

    customer: Mapped[Customer] = relationship("Customer", back_populates="orders")
    product: Mapped[Product] = relationship("Product", back_populates="orders")
    business: Mapped[User] = relationship("User", back_populates="orders")


# ==============================================================================
# CHAT MESSAGE
# ==============================================================================
class ChatMessage(Base):
    """Multi-tenant AI session log used to construct context vectors."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, nullable=False, index=True
    )

    active_tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    routing_state: Mapped[str] = mapped_column(String, default="DIRECT", nullable=False)

    role: Mapped[MessageRole] = mapped_column(EnumSQL(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    business: Mapped[User] = relationship("User", back_populates="chat_messages")

# ==============================================================================
# HANDOVER EVENT
# ==============================================================================
class HandoverEvent(Base):
    """Audit-trail row created every time AISHA emits [HANDOVER_REQUIRED].

    One row per escalation (not per customer) — unlike `ConversationState`,
    which only tracks the *current* live status for a customer, this is an
    immutable-except-status event log the notification engine reads once to
    build a `NotificationPayload`, and that later status updates (accepted /
    resolved) get written back onto.

    `conversation_id` points at `ConversationState.id` — the closest existing
    concept of "a conversation" in this schema, since `Conversation` rows are
    individual chat messages, not a conversation thread entity.
    """

    __tablename__ = "handover_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        "conversation_state_id",
        UUID(as_uuid=True),
        ForeignKey("conversation_states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshots — survive even if the customer record's name/phone later changes.
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)

    reason_code: Mapped[HandoverReasonCode] = mapped_column(
        EnumSQL(HandoverReasonCode), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_last_message: Mapped[str] = mapped_column(Text, nullable=False)

    waiting_start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[HandoverEventStatus] = mapped_column(
        EnumSQL(HandoverEventStatus),
        default=HandoverEventStatus.WAITING,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    business: Mapped[User] = relationship("User", back_populates="handover_events")
    conversation_state: Mapped[ConversationState] = relationship("ConversationState")
    customer: Mapped[Customer] = relationship("Customer")

    @property
    def waiting_seconds(self) -> float:
        """Seconds elapsed since `waiting_start_time`, computed on read —
        waiting time is intentionally never stored."""
        now = datetime.now(self.waiting_start_time.tzinfo)
        return max(0.0, (now - self.waiting_start_time).total_seconds())
    
    