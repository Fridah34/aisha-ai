import enum
import uuid

from app.database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    JSON,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Enum as EnumSQL,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

class OrderStatus(enum.Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"

class MessageSender(enum.Enum):
    customer = "customer"
    assistant = "assistant"
    human = "human"

#supported languages  en for ennglish, sw for swahili and sng for sheng'
class SupportedLanguages(enum.Enum):
    en = "en"
    sw = "sw"
    
class BusinessType(enum.Enum):
    retail = "retail"
    fashion = "fashion"
    services = "services"
    food = "food"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)
    business_name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)
    knowledge_base_text = Column(Text, nullable=True)
    business_type = Column(EnumSQL(BusinessType), nullable=False)
    
    # server_default=func.now() means PostgreSQL sets this automatically
    # More reliable than setting it in Python because it uses the
    # database server's clock, not your machine's clock
    whatsapp_phone_number_id = Column(String(100), unique = True, nullable= True)
    whatsapp_phone_number = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="owner")
    orders = relationship("Order", back_populates="business_owner")
    conversations = relationship("Conversation", back_populates="business_owner")
    conversation_states = relationship("ConversationState", back_populates="business_owner", foreign_keys="ConversationState.user_id",)
    #new: one business has many customers
    customers = relationship("Customer", back_populates="business_owner")
    #One business has many categories
    categories = relationship("Category", back_populates="business_owner")

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uq_category_per_business"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business_owner = relationship("User", back_populates="categories")

    # Single relationship back to Product, matched to Product.category
    # below. Previously there were two competing relationships here
    # (a `backref="products"` on Product.category AND this explicit
    # back_populates="category_obj") pointing at the same FK — that's a
    # duplicate relationship path over one column, which SQLAlchemy
    # either rejects at mapper-configuration time or resolves
    # ambiguously. One relationship per FK, named consistently on both
    # sides, is the correct pattern.
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, default=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    variant_label = Column(String(50), nullable=True)
    variant_options = Column(String(300), nullable=True)
    unit = Column(String(50), nullable=True)
    image_url = Column(String(500), nullable=True)
    upsell_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="products")
    order_items = relationship("Order", back_populates="product")
    category = relationship("Category", back_populates="products")

    @property
    def category_name(self):
        """
        Convenience read-only accessor — not a DB column. Lets
        ProductResponse (Pydantic, from_attributes=True) expose the
        related category's name without the caller needing to touch
        `.category.name` directly or risk an AttributeError if the
        product has no category (category_id is nullable).
        """
        return self.category.name if self.category else None


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        # uniqueness is now per business, not global
        UniqueConstraint("phone_number", "user_id", name="uq_customer_per_business"),
    )

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversations = relationship("Conversation", back_populates="customer")
    conversation_states = relationship("ConversationState", back_populates="customer")
    orders = relationship("Order", back_populates="customer")

    business_owner = relationship("User", back_populates="customers")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    sender = Column(EnumSQL(MessageSender), nullable=False)
    message_text = Column(Text, nullable=False)
    language = Column(EnumSQL(SupportedLanguages),default=SupportedLanguages.en, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    delivery_status = Column(String(20), nullable=True)

    customer = relationship("Customer", back_populates="conversations")
    business_owner = relationship("User", back_populates="conversations")


class HandoverStatus(enum.Enum):
    ai_active = "ai_active"
    needs_human = "needs_human"
    human_active = "human_active"
    resolved = "resolved"

class ConversationState(Base):
    __tablename__ = "conversation_states"
    __table_args__ = (
        UniqueConstraint("customer_id", "user_id", name="uq_customer_business"),
    )
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer,ForeignKey("users.id", ondelete= "CASCADE"), nullable=False)

    status = Column(EnumSQL(HandoverStatus), default=HandoverStatus.ai_active, nullable=False)
    #Tracks a short-lived "waiting for the customer to pick from a list" state,
    # e.g. "category_selection". Cleared as soon as it's resolved (matched or
    # handed to the LLM as a fallback). Kept generic so future list-based flows
    # (product selection, variant selection) don't each need their own column.
    pending_action = Column(String(50), nullable=True)
    taken_over_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    selected_business_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    selected_business_type = Column(String(50), nullable=True)
    selected_category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    customer = relationship("Customer", back_populates="conversation_states")
    business_owner = relationship("User", back_populates="conversation_states", foreign_keys=[user_id],)

class MarketplaceSession(Base):
    __tablename__ = "marketplace_sessions"
    
    id = Column(Integer, primary_key = True, index=True)
    phone_number = Column(String(20), unique=True,index=True, nullable=False)
    pending_action = Column(String(50), nullable= True)
    selected_business_type = Column(String(50), nullable=True)
    selected_business_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    selected_product_id = Column(Integer, ForeignKey("products.id", ondelete= "SET NULL"), nullable=True)
    selected_size = Column(String(20),nullable=True)
    # Tracks which page of a paginated List Picker menu (categories or
    # stores) the customer is currently on, in units of PAGE_SIZE (see
    # marketplace_flow.py). Needed because WhatsApp's list-picker interactive
    # message is hard-capped at 10 rows total (Meta platform limit, not a
    # Twilio restriction) — once category/store counts exceed that, browsing
    # becomes a multi-page "More options" flow, and this is what lets the
    # session remember which page a reply should resolve against.
    # server_default="0" so existing rows backfill cleanly on migration.
    list_offset = Column(Integer, default=0, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (
        UniqueConstraint("phone_number", "business_id", name="uq_cart per_business"),   
    )
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), index=True, nullable=False)
    business_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    items = Column(JSON, default=list, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_group_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    customer_id = Column(Integer,ForeignKey("customers.id", ondelete="SET NULL"),nullable=True)
    product_id = Column(Integer,ForeignKey("products.id", ondelete="SET NULL"),nullable=True)

    user_id = Column(Integer,ForeignKey("users.id", ondelete="SET NULL"),nullable=True)

    quantity = Column(Integer, default=1, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(EnumSQL(OrderStatus), default=OrderStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    snapshot_customer_name = Column(String, nullable=True)
    snapshot_customer_phone = Column(String, nullable=True)
    snapshot_product_name = Column(String, nullable=True)
    snapshot_product_price = Column(Numeric(10, 2), nullable=True)
    snapshot_business_name = Column(String, nullable=True)


    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product", back_populates="order_items")
    business_owner = relationship("User", back_populates="orders")
    