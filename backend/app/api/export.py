from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from ..db.base import get_db
from ..models.database import ItemForSale, Apartment, User, Message, Group

router = APIRouter()


def _contact_str(info) -> Optional[str]:
    if not info:
        return None
    if isinstance(info, dict):
        return info.get("raw") or None
    return str(info)


@router.get("/items/json")
async def export_items_json(
    after: Optional[datetime] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    # Join with users, messages, and groups to get complete info
    q = db.query(ItemForSale, User, Message, Group).join(
        User, ItemForSale.user_id == User.id
    ).join(
        Message, ItemForSale.message_id == Message.id
    ).join(
        Group, Message.group_id == Group.id
    ).filter(ItemForSale.availability_status == "available")
    
    if after:
        q = q.filter(ItemForSale.posted_date > after)
    
    rows = q.order_by(ItemForSale.posted_date.desc()).limit(limit).all()
    return [
        {
            "category": "item_for_sale",
            "title": r[0].title,
            "description": r[0].description,
            "price": float(r[0].price) if r[0].price is not None else None,
            "item_category": r[0].category,
            "condition": r[0].condition,
            "location": r[0].location,
            "posted_date": r[0].posted_date,
            "contact": _contact_str(r[0].contact_info),
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


@router.get("/apartments/json")
async def export_apartments_json(
    after: Optional[datetime] = Query(None),
    listing_type: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    # Join with users, messages, and groups to get complete info
    q = db.query(Apartment, User, Message, Group).join(
        User, Apartment.user_id == User.id
    ).join(
        Message, Apartment.message_id == Message.id
    ).join(
        Group, Message.group_id == Group.id
    ).filter(Apartment.availability_status == "available")
    
    if after:
        q = q.filter(Apartment.posted_date > after)
    if listing_type:
        q = q.filter(Apartment.listing_type == listing_type)
    
    rows = q.order_by(Apartment.posted_date.desc()).limit(limit).all()
    return [
        {
            "category": r[0].listing_type,
            "address": r[0].address,
            "price_per_month": float(r[0].price_per_month) if r[0].price_per_month is not None else None,
            "bedrooms": r[0].bedrooms,
            "bathrooms": r[0].bathrooms,
            "lease_duration": r[0].lease_duration,
            "posted_date": r[0].posted_date,
            "contact": _contact_str(r[0].contact_info),
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


@router.get("/messages/json")
async def export_messages_json(
    after: Optional[datetime] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    q = db.query(Message)
    if after:
        q = q.filter(Message.timestamp > after)
    rows: List[Message] = q.order_by(Message.timestamp.desc()).limit(limit).all()
    return [
        {
            "message_id": r.message_id,
            "timestamp": r.timestamp,
            "content": r.content,
            "links": r.links,
            "user_id": str(r.user_id) if r.user_id else None,
            "group_id": str(r.group_id) if r.group_id else None,
        }
        for r in rows
    ]


@router.get("/apartments/text")
async def export_apartments_text(
    listing_type: Optional[str] = Query(None),
    after: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Apartment).filter(Apartment.availability_status == "available")
    if listing_type:
        q = q.filter(Apartment.listing_type == listing_type)
    if after:
        q = q.filter(Apartment.posted_date > after)
    rows: List[Apartment] = q.order_by(Apartment.posted_date.desc()).limit(limit).all()
    lines: List[str] = []
    for r in rows:
        line = f"[{r.posted_date:%Y-%m-%d}] {r.listing_type.upper()}: {r.address or 'N/A'} - ${float(r.price_per_month) if r.price_per_month else 'N/A'} | Contact: {_contact_str(r.contact_info) or 'N/A'}"
        lines.append(line)
    return {"text": "\n".join(lines)}


@router.get("/items/text")
async def export_items_text(
    after: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(ItemForSale).filter(ItemForSale.availability_status == "available")
    if after:
        q = q.filter(ItemForSale.posted_date > after)
    rows: List[ItemForSale] = q.order_by(ItemForSale.posted_date.desc()).limit(limit).all()
    lines: List[str] = []
    for r in rows:
        line = f"[{r.posted_date:%Y-%m-%d}] {r.title} - ${float(r.price) if r.price else 'N/A'} ({r.category}) | Contact: {_contact_str(r.contact_info) or 'N/A'}"
        lines.append(line)
    return {"text": "\n".join(lines)}
