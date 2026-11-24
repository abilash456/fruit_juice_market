from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = "customer"
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    price: float
    original_price: float = 0
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")
    emoji: str = "🍹"
    stock: int = 0
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="user.id")
    customer_name: str
    address: str
    phone: str
    total: float
    payment_method: str = "Cash on Delivery"
    payment_status: str = "Pending"
    status: str = "Pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    product_name: str
    quantity: int
    unit_price: float

class WishlistItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    product_id: int = Field(foreign_key="product.id")

class SupportTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    subject: str
    category: str
    message: str
    status: str = "Open"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    product_id: int = Field(foreign_key="product.id")

    rating: int = Field(ge=1, le=5)
    comment: str

    is_approved: bool = False

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
