from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"

class MessageSender(str, Enum):
    customer = "customer"
    assistant = "assistant"
    human = "human"

class SupportedLanguages(str, Enum):
    en = "en"
    sw = "sw"

class userRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field()
    password: str = Field(min_length=6, max_length=100)
    business_name: str = Field(min_length=1, max_length=150)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Eve Mipata",
                "email": "eve.mipata@example.com",
                "password": "securepassword",
                "business_name": "Eve's Business"
            }
        }

class userGoogleRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field()
    google_id: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=150)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Eve Mipata",
                "email": "eve.mipata@example.com",
                "google_id": "google-oauth2|1234567890",
                "business_name": "Eve's Business"
            }
        }

class userLogin(BaseModel):
    email: EmailStr = Field()
    password: str = Field(min_length=6, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "eve.mipata@example.com",
                "password": "securepassword"
            }
        }

class userResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    business_name: str
    is_active: bool
    created_at: datetime

    class  Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Eve Mipata",
                "email": "eve.mipata@example.com",
                "business_name": "Eve's Business",
                "is_active": True,
                "created_at": "2026-06-11T14:00:00"
            }
        }

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6IkV2ZSBNaXBhdGEiLCJpYXQiOjE2ODYyMDg0MDB9.4f8e5b8c9d3e2f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7",
                "token_type": "bearer"
            }
        }

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    is_available: Optional[bool] = True

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Product 1",
                "description": "This is a great product.",
                "price": 19.99,
                "is_available": True
            }
        }

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    is_available: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Product Name",
                "description": "Updated description.",
                "price": 24.99,
                "is_available": False
            }
        }

class ProductResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    price: Decimal
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "name": "Product 1",
                "description": "This is a great product.",
                "price": 19.99,
                "is_available": True,
                "created_at": "2026-06-11T14:00:00",
                "updated_at": "2026-06-11T14:00:00"
            }
        }

class CustomerResponse(BaseModel):
    id: int
    phone_number: str
    name: Optional[str]
    is_active: bool
    deleted_at: Optional[datetime]
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "phone_number": "+1234567890",
                "name": "John Doe",
                "is_active": True,
                "deleted_at": None,
                "first_seen": "2026-06-11T14:00:00",
                "last_seen": "2026-06-11T14:00:00"
            }
        }

class ConversationCreate(BaseModel):
    customer_id: int
    user_id: int 
    sender: MessageSender
    message: str = Field(min_length=1, max_length=2000)
    language: SupportedLanguages = Field(default=SupportedLanguages.en)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": 1,
                "user_id": 1,
                "sender": "customer",
                "message": "Hello, I have a question about my order.",
                "language": "en"
            }
        }

class ConversationResponse(BaseModel):
    id: int
    customer_id: int
    user_id: int
    sender: MessageSender
    message: str
    language: SupportedLanguages
    timestamp: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "customer_id": 1,
                "user_id": 1,
                "sender": "customer",
                "message_text": "Hello, I have a question about my order.",
                "language": "en",
                "timestamp": "2026-06-11T14:00:00"
            }
        }

class ConversationHistoryResponse(BaseModel):
    customer_id: int
    messages:List[ConversationResponse]

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    user_id: Optional[int] = None
    quantity: int = Field(..., gt=0)
    total_amount: Decimal = Field(..., gt=0, decimal_places=2)
    status: OrderStatus = Field(default=OrderStatus.pending)

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": 1,
                "product_id": 1,
                "user_id": 1,
                "quantity": 2,
                "total_amount": 39.98,
                "status": "pending"
            }
        }

class OrderUpdate(BaseModel):
    status: OrderStatus
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "shipped"
            }
        }

class OrderResponse(BaseModel):
    id: int
    customer_id: Optional[int]
    product_id: Optional[int]
    user_id: Optional[int]
    quantity: int
    total_amount: Decimal
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    snapshot_customer_name: Optional[str]
    snapshot_customer_phone: Optional[str]
    snapshot_product_name: Optional[str]
    snapshot_product_price: Optional[Decimal]
    snapshot_business_name: Optional[str]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "customer_id": 1,
                "product_id": 1,
                "user_id": 1,
                "quantity": 2,
                "total_amount": 39.98,
                "status": "pending",
                "created_at": "2026-06-11T14:00:00",
                "updated_at": "2026-06-11T14:00:00"
            }
        }
