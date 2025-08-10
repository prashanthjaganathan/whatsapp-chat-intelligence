from pydantic import BaseModel, UUID4
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

class ApartmentBase(BaseModel):
    listing_type: str
    address: Optional[str] = None
    price_per_month: Optional[Decimal] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    lease_duration: Optional[str] = None
    furnished: Optional[bool] = None
    utilities_included: Optional[bool] = None
    pet_friendly: Optional[bool] = None

class ApartmentResponse(ApartmentBase):
    id: UUID4
    listing_id: str
    availability_status: str
    posted_date: datetime
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    amenities: List[str] = []
    key_features: List[str] = []
    view_count: int
    inquiry_count: int
    contact_info: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class ApartmentSearch(BaseModel):
    query: str
    listing_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    furnished: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    utilities_included: Optional[bool] = None