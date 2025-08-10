from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ..db.base import get_db
from ..models.database import ItemForSale, User, Message
from ..schemas.items import ItemResponse, ItemCreate, ItemUpdate, ItemSearch

router = APIRouter()

@router.get("/", response_model=List[ItemResponse])
async def get_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    condition: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    availability_status: str = Query("available"),
    db: Session = Depends(get_db)
):
    """Get all items with filtering options."""
    query = db.query(ItemForSale).join(User).join(Message)
    
    # Apply filters
    if category:
        query = query.filter(ItemForSale.category == category)
    if min_price is not None:
        query = query.filter(ItemForSale.price >= min_price)
    if max_price is not None:
        query = query.filter(ItemForSale.price <= max_price)
    if condition:
        query = query.filter(ItemForSale.condition == condition)
    if location:
        query = query.filter(ItemForSale.location.ilike(f"%{location}%"))
    if availability_status:
        query = query.filter(ItemForSale.availability_status == availability_status)
    
    # Order by posted date (newest first)
    query = query.order_by(ItemForSale.posted_date.desc())
    
    items = query.offset(skip).limit(limit).all()
    return items

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: UUID, db: Session = Depends(get_db)):
    """Get specific item by ID."""
    item = db.query(ItemForSale).filter(ItemForSale.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Increment view count
    item.view_count += 1
    db.commit()
    
    return item

@router.get("/search/", response_model=List[ItemResponse])
async def search_items(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search items by text query."""
    query = db.query(ItemForSale).filter(
        ItemForSale.availability_status == "available"
    ).filter(
        (ItemForSale.title.ilike(f"%{q}%")) |
        (ItemForSale.description.ilike(f"%{q}%")) |
        (ItemForSale.category.ilike(f"%{q}%"))
    ).order_by(ItemForSale.posted_date.desc())
    
    items = query.offset(skip).limit(limit).all()
    return items

@router.get("/categories/")
async def get_categories(db: Session = Depends(get_db)):
    """Get all item categories."""
    categories = db.query(ItemForSale.category).distinct().all()
    return [cat[0] for cat in categories if cat[0]]

@router.get("/user/{user_id}", response_model=List[ItemResponse])
async def get_user_items(
    user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get items by specific user."""
    items = db.query(ItemForSale).filter(
        ItemForSale.user_id == user_id
    ).order_by(ItemForSale.posted_date.desc()).offset(skip).limit(limit).all()
    
    return items

@router.put("/{item_id}/status")
async def update_item_status(
    item_id: UUID,
    status: str = Query(..., regex="^(available|sold|pending)$"),
    db: Session = Depends(get_db)
):
    """Update item availability status."""
    item = db.query(ItemForSale).filter(ItemForSale.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.availability_status = status
    db.commit()
    
    return {"message": "Status updated successfully", "status": status}

@router.post("/{item_id}/inquire")
async def inquire_about_item(item_id: UUID, db: Session = Depends(get_db)):
    """Track inquiry about an item."""
    item = db.query(ItemForSale).filter(ItemForSale.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.inquiry_count += 1
    db.commit()
    
    return {"message": "Inquiry recorded"}