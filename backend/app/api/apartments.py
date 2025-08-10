from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from ..db.base import get_db
from ..models.database import Apartment, User, Message
from ..schemas.apartments import ApartmentResponse, ApartmentSearch

router = APIRouter()

@router.get("/", response_model=List[ApartmentResponse])
async def get_apartments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    listing_type: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    bedrooms: Optional[int] = Query(None, ge=0),
    bathrooms: Optional[float] = Query(None, ge=0),
    furnished: Optional[bool] = Query(None),
    pet_friendly: Optional[bool] = Query(None),
    utilities_included: Optional[bool] = Query(None),
    availability_status: str = Query("available"),
    db: Session = Depends(get_db)
):
    """Get all apartments with filtering options."""
    query = db.query(Apartment).join(User).join(Message)
    
    # Apply filters
    if listing_type:
        query = query.filter(Apartment.listing_type == listing_type)
    if min_price is not None:
        query = query.filter(Apartment.price_per_month >= min_price)
    if max_price is not None:
        query = query.filter(Apartment.price_per_month <= max_price)
    if bedrooms is not None:
        query = query.filter(Apartment.bedrooms == bedrooms)
    if bathrooms is not None:
        query = query.filter(Apartment.bathrooms >= bathrooms)
    if furnished is not None:
        query = query.filter(Apartment.furnished == furnished)
    if pet_friendly is not None:
        query = query.filter(Apartment.pet_friendly == pet_friendly)
    if utilities_included is not None:
        query = query.filter(Apartment.utilities_included == utilities_included)
    if availability_status:
        query = query.filter(Apartment.availability_status == availability_status)
    
    # Order by posted date (newest first)
    query = query.order_by(Apartment.posted_date.desc())
    
    apartments = query.offset(skip).limit(limit).all()
    return apartments

@router.get("/{apartment_id}", response_model=ApartmentResponse)
async def get_apartment(apartment_id: UUID, db: Session = Depends(get_db)):
    """Get specific apartment by ID."""
    apartment = db.query(Apartment).filter(Apartment.id == apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    # Increment view count
    apartment.view_count += 1
    db.commit()
    
    return apartment

@router.get("/search/", response_model=List[ApartmentResponse])
async def search_apartments(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search apartments by text query."""
    query = db.query(Apartment).filter(
        Apartment.availability_status == "available"
    ).filter(
        (Apartment.address.ilike(f"%{q}%")) |
        (Apartment.listing_type.ilike(f"%{q}%"))
    ).order_by(Apartment.posted_date.desc())
    
    apartments = query.offset(skip).limit(limit).all()
    return apartments

@router.get("/filters/")
async def get_available_filters(db: Session = Depends(get_db)):
    """Get available filter options."""
    listing_types = db.query(Apartment.listing_type).distinct().all()
    
    return {
        "listing_types": [lt[0] for lt in listing_types if lt[0]],
        "price_ranges": [
            {"label": "Under $500", "min": 0, "max": 500},
            {"label": "$500-$1000", "min": 500, "max": 1000},
            {"label": "$1000-$2000", "min": 1000, "max": 2000},
            {"label": "$2000+", "min": 2000, "max": None}
        ],
        "bedrooms": [1, 2, 3, 4, 5],
        "bathrooms": [1, 1.5, 2, 2.5, 3]
    }

@router.post("/{apartment_id}/inquire")
async def inquire_about_apartment(apartment_id: UUID, db: Session = Depends(get_db)):
    """Track inquiry about an apartment."""
    apartment = db.query(Apartment).filter(Apartment.id == apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    apartment.inquiry_count += 1
    db.commit()
    
    return {"message": "Inquiry recorded"}

@router.put("/{apartment_id}/status")
async def update_apartment_status(
    apartment_id: UUID,
    status: str = Query(..., regex="^(available|rented|pending)$"),
    db: Session = Depends(get_db)
):
    """Update apartment availability status."""
    apartment = db.query(Apartment).filter(Apartment.id == apartment_id).first()
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    
    apartment.availability_status = status
    db.commit()
    
    return {"message": "Status updated successfully", "status": status}