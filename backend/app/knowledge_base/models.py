# Enable modern string-based type hinting to prevent version evaluation crashes
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal  # Guarding against floating-point transaction errors

from app.database import Base
from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    """The master account identity table for registered retail shop merchants."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    business_name: Mapped[str] = mapped_column(String, nullable=False)


class Product(Base):
    """The physical transactional product catalog inventory tracking layer."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # ADDED: index=True for fast multi-tenant queries
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False, 
        index=True  
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # FIXED: Type-mapped safely to Decimal to prevent KES currency precision errors
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False) 
    currency: Mapped[str] = mapped_column(String(3), default="KES")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stock_quantity: Mapped[int | None] = mapped_column(nullable=True)


class ChatMessage(Base):
    """
    The multi-tenant chat log table, storing individual message frames.
    Enhanced with session grouping and fast index searching.
    """
    # FIXED: Renamed to semantically match message-level rows
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # ADDED: index=True to instantly fetch messages belonging to a specific tenant
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False, 
        index=True  
    )
    
    # ADDED: session_id to group chat logs into clean, manageable threads
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        default=uuid.uuid4, 
        nullable=False, 
        index=True
    )
    
    # Marketplace Hub Proxy variables
    active_tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    routing_state: Mapped[str] = mapped_column(String, default="DIRECT", nullable=False) # 'DIRECT' vs 'FORWARDED'
    
    role: Mapped[str] = mapped_column(String, nullable=False) # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # ADDED: index=True so you can instantly sort messages from newest to oldest
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        index=True  
    )

