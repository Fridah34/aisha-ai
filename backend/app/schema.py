import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from app.auth.utils import is_password_strong
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class MessageRole(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    HUMAN = "HUMAN"


class Language(str, Enum):
    EN = "EN"
    SW = "SW"


class SupportedLanguages(str, Enum):
    en = "en"
    sw = "sw"


class BusinessType(str, Enum):
    retail = "retail"
    fashion = "fashion"
    services = "services"
    food = "food"


# ==========USER SCHEMAS==========


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field(description="Unique email address")
    password: str = Field(
        min_length=8,
        max_length=100,
        description="Password with a minimum of 8 characters",
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=100, description="Password confirmation"
    )
    business_name: str = Field(
        min_length=1, max_length=150, description="Business name"
    )
    business_type: BusinessType = Field(description="Type of business")

    #  This checks that both fields match automatically!
    @model_validator(mode="after")
    def verify_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    # Enforces real formatting checks and explicitly bans placeholder domains
    @field_validator("email")
    @classmethod
    def block_fake_testing_domains(cls, value: str) -> str:
        lowercase_email = value.lower()

        bad_domains = ["example.com", "test.com", "invalid.com", "fake.com"]
        if any(domain in lowercase_email for domain in bad_domains):
            raise ValueError(
                "Please use a real email address, not a placeholder domain."
            )

        return value

    # Automatically  hooks ito your custom ' is _password_strong' utility rule
    @field_validator("password")
    @classmethod
    def enforce_strong_passwords(cls, value: str) -> str:
        if not is_password_strong(value):
            raise ValueError("Password is not strong enough.")

        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Eve Mipata",
                "email": "eve.mipata@example.com",
                "password": "securepassword",
                "confirm_password": "securepassword",
                "business_name": "Eve's Business",
                "business_type": "retail",
            }
        }
    )


class UserGoogleRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Full name")
    email: EmailStr = Field()
    google_id: str = Field(min_length=1, max_length=255)
    business_name: str = Field(min_length=1, max_length=150)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Eve Mipata",
                "email": "eve.mipata@example.com",
                "google_id": "google-oauth2|1234567890",
                "business_name": "Eve's Business",
            }
        }
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(description="Registered email address")
    password: str = Field(min_length=8, max_length=100, description="Account password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "eve.mipata@example.com", "password": "securepassword"}
        }
    )


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    business_name: Optional[str] = None
    is_active: bool
    google_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Eve Mipata",
                "email": "eve.mipata@example.com",
                "business_name": "Eve's Business",
                "is_active": True,
                "created_at": "2026-06-11T14:00:00",
            }
        },
    )


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(description="Authenticated user details")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6IkV2ZSBNaXBhdGEiLCJpYXQiOjE2ODYyMDg0MDB9.4f8e5b8c9d3e2f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7",
                "token_type": "bearer",
                "user": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "name": "Eve Mipata",
                    "email": "eve.mipata@example.com",
                    "business_name": "Eve's Business",
                    "is_active": True,
                    "created_at": "2026-06-11T14:00:00",
                },
            }
        },
    )


# ==========PRODUCT SCHEMAS==========


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    is_available: Optional[bool] = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Product 1",
                "description": "This is a great product.",
                "price": 19.99,
                "is_available": True,
            }
        }
    )


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    is_available: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Product Name",
                "description": "Updated description.",
                "price": 24.99,
                "is_available": False,
            }
        }
    )


class ProductResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: Optional[str]
    price: float
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "business_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Product 1",
                "description": "This is a great product.",
                "price": 19.99,
                "is_available": True,
                "created_at": "2026-06-11T14:00:00",
                "updated_at": "2026-06-11T14:00:00",
            }
        },
    )


# =========CUSTOMER SCHEMAS==========


class CustomerResponse(BaseModel):
    id: uuid.UUID
    phone_number: str
    name: Optional[str]
    is_active: bool
    deleted_at: Optional[datetime]
    first_seen: datetime
    last_seen: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "phone_number": "+1234567890",
                "name": "John Doe",
                "is_active": True,
                "deleted_at": None,
                "first_seen": "2026-06-11T14:00:00",
                "last_seen": "2026-06-11T14:00:00",
            }
        },
    )


class ConversationCreate(BaseModel):
    customer_id: uuid.UUID
    business_id: uuid.UUID
    role: MessageRole
    content: str = Field(min_length=1, max_length=2000)
    language: Language = Field(default=Language.EN)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "business_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "role": "USER",
                "content": "Hello, I have a question about my order.",
                "language": "EN",
            }
        }
    )


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    business_id: uuid.UUID
    role: MessageRole
    content: str
    language: Language
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "business_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "role": "USER",
                "content": "Hello, I have a question about my order.",
                "language": "EN",
                "created_at": "2026-06-11T14:00:00",
            }
        },
    )


class ConversationHistoryResponse(BaseModel):
    customer_id: uuid.UUID
    messages: List[ConversationResponse]

    model_config = ConfigDict(from_attributes=True)


# =========ORDER SCHEMAS==========


class OrderCreate(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    business_id: Optional[uuid.UUID] = None
    quantity: int = Field(..., gt=0)
    total_amount: Decimal = Field(..., gt=0, decimal_places=2)
    status: OrderStatus = Field(default=OrderStatus.PENDING)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "business_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "quantity": 2,
                "total_amount": 39.98,
                "status": "PENDING",
            }
        }
    )


class OrderUpdate(BaseModel):
    status: OrderStatus

    model_config = ConfigDict(json_schema_extra={"example": {"status": "SHIPPED"}})


class OrderResponse(BaseModel):
    id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    product_id: Optional[uuid.UUID]
    business_id: Optional[uuid.UUID]
    quantity: int
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    snapshot_customer_name: Optional[str]
    snapshot_customer_phone: Optional[str]
    snapshot_product_name: Optional[str]
    snapshot_product_price: Optional[float]
    snapshot_business_name: Optional[str]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "customer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "business_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "quantity": 2,
                "total_amount": 39.98,
                "status": "PENDING",
                "created_at": "2026-06-11T14:00:00",
                "updated_at": "2026-06-11T14:00:00",
                "snapshot_customer_name": "John Doe",
                "snapshot_customer_phone": "+1234567890",
                "snapshot_product_name": "Product 1",
                "snapshot_product_price": 19.99,
                "snapshot_business_name": "Eve's Business",
            }
        },
    )
