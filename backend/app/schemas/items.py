from pydantic import BaseModel, UUID4
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    availability_status: Optional[str] = None

class ItemResponse(ItemBase):
    id: UUID4
    item_id: str
    availability_status: str
    posted_date: datetime
    view_count: int
    inquiry_count: int
    contact_info: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ItemSearch(BaseModel):
    query: str
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    condition: Optional[str] = None
    location: Optional[str] = None