from sqlalchemy import (
    Column, Integer, String, Text, Boolean,

    DateTime, ForeignKey, Numeric, Enum as EnumSQL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base
from sqlalchemy import text


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

#supported languages  en for english, sw for swahili and sng for sheng'
class SupportedLanguages(enum.Enum):
    en = "en"
    sw = "sw"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)
    business_name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    products = relationship("Product", back_populates="owner")
    orders = relationship("Order", back_populates="business_owner")
    conversations = relationship("Conversation", back_populates="business_owner")

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="products")
    order_items = relationship("Order", back_populates="product")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversations = relationship("Conversation", back_populates="customer")
    orders = relationship("Order", back_populates="customer")

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

    customer = relationship("Customer", back_populates="conversations")
    business_owner = relationship("User", back_populates="conversations")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

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