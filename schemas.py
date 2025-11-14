"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

class Video(BaseModel):
    """Simple user-generated video entries
    Collection name: "video"
    """
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    video_url: Optional[str] = Field(None, description="Hosted video URL (e.g., YouTube link)")
    thumbnail_url: Optional[str] = Field(None, description="Optional thumbnail URL")
    creator: Optional[str] = Field(None, description="Creator name or user id")

class TradeAccount(BaseModel):
    """Paper trading account for a user
    Collection name: "tradeaccount"
    """
    user_id: str = Field(..., description="User identifier")
    cash_balance: float = Field(10000.0, ge=0, description="Available cash for trading")
    positions: Dict[str, float] = Field(default_factory=dict, description="Symbol -> shares owned")

class Order(BaseModel):
    """Trade orders (paper trading)
    Collection name: "order"
    """
    user_id: str = Field(..., description="User identifier")
    symbol: str = Field(..., description="Ticker symbol")
    side: Literal['buy','sell'] = Field(..., description="Buy or sell")
    quantity: float = Field(..., gt=0, description="Number of shares")
    price: float = Field(..., gt=0, description="Execution price per share")
    status: Literal['filled','rejected'] = Field('filled', description="Order status")
    reason: Optional[str] = Field(None, description="If rejected, reason")

# Add your own schemas here:
# --------------------------------------------------

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
