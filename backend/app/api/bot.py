from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from ..db.base import get_db
from ..models.database import ItemForSale, Apartment, User, Message, Group

router = APIRouter()

@router.get("/most-recent/items")
async def most_recent_items(
    limit: int = Query(10, ge=1, le=50),
    after: Optional[datetime] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    # Join with users, messages, and groups to get complete info
    query = db.query(ItemForSale, User, Message, Group).join(
        User, ItemForSale.user_id == User.id
    ).join(
        Message, ItemForSale.message_id == Message.id
    ).join(
        Group, Message.group_id == Group.id
    ).filter(ItemForSale.availability_status == "available")
    
    if after:
        query = query.filter(ItemForSale.posted_date > after)
    if q:
        query = query.filter(
            (ItemForSale.title.ilike(f"%{q}%")) | 
            (ItemForSale.description.ilike(f"%{q}%")) |
            (User.display_name.ilike(f"%{q}%")) |
            (Group.group_name.ilike(f"%{q}%"))
        )
    
    rows = query.order_by(ItemForSale.posted_date.desc()).limit(limit).all()
    
    def contact(info):
        if not info:
            return None
        return info.get("raw") if isinstance(info, dict) else str(info)
    
    return [
        {
            "title": r[0].title,
            "price": float(r[0].price) if r[0].price is not None else None,
            "category": r[0].category,
            "posted_date": r[0].posted_date,
            "contact": contact(r[0].contact_info),
            "location": r[0].location,
            "item_id": r[0].item_id,
            # New fields for seller and group info
            "seller_name": r[1].display_name if r[1] else "Unknown",
            "seller_phone": r[1].phone_number if r[1] else None,
            "group_name": r[3].group_name if r[3] else "Unknown",
            "message_id": r[2].message_id if r[2] else None,
            "original_message": r[2].content if r[2] else None,
            "message_timestamp": r[2].timestamp if r[2] else None,
        }
        for r in rows
    ]

@router.get("/most-recent/apartments")
async def most_recent_apartments(
    limit: int = Query(10, ge=1, le=50),
    after: Optional[datetime] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    # Join with users, messages, and groups to get complete info
    query = db.query(Apartment, User, Message, Group).join(
        User, Apartment.user_id == User.id
    ).join(
        Message, Apartment.message_id == Message.id
    ).join(
        Group, Message.group_id == Group.id
    ).filter(Apartment.availability_status == "available")
    
    if after:
        query = query.filter(Apartment.posted_date > after)
    if q:
        query = query.filter(
            (Apartment.address.ilike(f"%{q}%")) | 
            (Apartment.listing_type.ilike(f"%{q}%")) |
            (User.display_name.ilike(f"%{q}%")) |
            (Group.group_name.ilike(f"%{q}%"))
        )
    
    rows = query.order_by(Apartment.posted_date.desc()).limit(limit).all()
    
    def contact(info):
        if not info:
            return None
        return info.get("raw") if isinstance(info, dict) else str(info)
    
    return [
        {
            "listing_type": r[0].listing_type,
            "address": r[0].address,
            "price_per_month": float(r[0].price_per_month) if r[0].price_per_month is not None else None,
            "posted_date": r[0].posted_date,
            "contact": contact(r[0].contact_info),
            "listing_id": r[0].listing_id,
            # New fields for seller and group info
            "seller_name": r[1].display_name if r[1] else "Unknown",
            "seller_phone": r[1].phone_number if r[1] else None,
            "group_name": r[3].group_name if r[3] else "Unknown",
            "message_id": r[2].message_id if r[2] else None,
            "original_message": r[2].content if r[2] else None,
            "message_timestamp": r[2].timestamp if r[2] else None,
        }
        for r in rows
    ]