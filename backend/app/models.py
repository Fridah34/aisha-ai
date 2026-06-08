from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Numeric, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


# ─── ENUMS ───────────────────────────────────────────────────────────────────
# Enums restrict a column to only specific values
# Nobody can set order status to "random" — only pending/confirmed/fulfilled
# Python enum maps directly to a PostgreSQL ENUM type in the database

class OrderStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    fulfilled = "fulfilled"


class MessageSender(enum.Enum):
    customer = "customer"
    assistant = "assistant"


# ─── USER (Business Owner) ───────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)

    # nullable=True because Google OAuth users won't have a password
    # We'll implement Google OAuth later — the column is ready for it now
    hashed_password = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)

    business_name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)

    # server_default=func.now() means PostgreSQL sets this automatically
    # More reliable than setting it in Python because it uses the
    # database server's clock, not your machine's clock
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships tell SQLAlchemy how tables connect
    # When you access user.products, SQLAlchemy automatically
    # runs the JOIN — you never write that SQL yourself
    products = relationship("Product", back_populates="owner")
    orders = relationship("Order", back_populates="business_owner")


# ─── PRODUCT ─────────────────────────────────────────────────────────────────
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # ForeignKey creates the link between tables
    # ondelete="CASCADE" means if the business owner (user) is deleted,
    # all their products are automatically deleted too
    # Without this, deleting a user would leave orphaned products
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Always use Numeric for money — never Float
    # Float has rounding errors: 4500.00 might become 4499.9999999
    # Numeric(10, 2) = up to 10 digits total, exactly 2 after decimal
    price = Column(Numeric(10, 2), nullable=False)

    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # onupdate=func.now() automatically updates this column
    # every time this row is modified — you never set it manually
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="products")
    order_items = relationship("Order", back_populates="product")


# ─── CUSTOMER (WhatsApp User) ─────────────────────────────────────────────────
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    # Phone number is the customer's unique identity
    # They never create accounts — their WhatsApp number IS who they are
    # index=True makes lookups by phone number fast
    phone_number = Column(String(20), unique=True, index=True, nullable=False)

    # Name starts as null — AISHA collects it during conversation
    name = Column(String(100), nullable=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())

    conversations = relationship("Conversation", back_populates="customer")
    orders = relationship("Order", back_populates="customer")


# ─── CONVERSATION (Every single message) ─────────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )

    # Which business this conversation belongs to
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Every row is one message — both directions
    # sender tells us who wrote it: the customer or AISHA
    sender = Column(Enum(MessageSender), nullable=False)
    message_text = Column(Text, nullable=False)

    # "en" for English, "sw" for Kiswahili
    # AISHA detects this automatically and responds in the same language
    language = Column(String(10), default="en")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="conversations")
    business_owner = relationship("User")


# ─── ORDER ────────────────────────────────────────────────────────────────────
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )

    # ondelete="SET NULL" instead of CASCADE here — important difference
    # If a product is deleted, we don't want to lose the order history
    # The order stays but product_id becomes NULL
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    # Which business owner this order belongs to
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    quantity = Column(Integer, default=1, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product", back_populates="order_items")
    business_owner = relationship("User", back_populates="orders")