from __future__ import annotations

from typing import List, Optional, Literal
from datetime import date
from pydantic import BaseModel, Field, EmailStr


# High-level categorization
class CategorizationResult(BaseModel):
    category: Literal["ITEM_FOR_SALE", "APARTMENT_LISTING", "GENERAL"] = Field(
        description="Top-level classification for the message"
    )


# Item for sale extraction schema
class SalesExtraction(BaseModel):
    title: str = Field(description="Brief item title")
    description: Optional[str] = Field(default=None, description="Full description")
    price: Optional[float] = Field(default=None, description="Price as a number (no currency symbol)")
    category: Optional[
        Literal[
            "furniture",
            "electronics",
            "textbooks",
            "clothing",
            "appliances",
            "kitchen",
            "study-materials",
            "decorations",
            "other",
        ]
    ] = Field(default=None, description="Normalized item category")
    condition: Optional[Literal["new", "like_new", "good", "fair", "poor"]] = None
    contact_phone: Optional[str] = Field(default=None, description="Seller phone if present")
    contact_email: Optional[EmailStr] = Field(default=None, description="Seller email if present")
    location: Optional[str] = Field(default=None, description="Location or pickup area")
    images_mentioned: Optional[bool] = Field(default=None, description="Whether the text mentions images")


# Housing extraction schema
class HousingExtraction(BaseModel):
    listing_type: Literal["roommate_wanted", "sublet", "rental", "room_available"]
    address: Optional[str] = None
    price: Optional[float] = Field(default=None, description="Monthly rent as a number")
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    lease_duration: Optional[str] = None
    available_from: Optional[date] = Field(default=None, description="ISO date if present")
    available_until: Optional[date] = Field(default=None, description="ISO date if present")
    amenities: List[str] = Field(default_factory=list)
    furnished: Optional[bool] = None
    utilities_included: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    contact_phone: Optional[str] = Field(default=None, description="Contact phone if present")
    contact_email: Optional[EmailStr] = Field(default=None, description="Contact email if present")
    key_features: List[str] = Field(default_factory=list) 