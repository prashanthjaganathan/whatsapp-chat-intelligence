from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from ..db.base import get_db
from ..services.chat_ingest import ChatIngestService

router = APIRouter()

@router.post("/chat-export")
async def ingest_chat_export(
    file: UploadFile = File(..., description="attach a `.txt` export from WhatsApp"),
    since: Optional[str] = Query(None, description="Only ingest messages strictly after this UTC timestamp. Format: `YYYY-MM-DDTHH:MM:SS` or `YYYY-MM-DD`"),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    text = contents.decode("utf-8", errors="replace")
    
    # Parse the since parameter properly
    since_dt = None
    if since:
        try:
            # Try parsing as full datetime first
            if 'T' in since:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            else:
                # If just date, assume midnight UTC
                since_dt = datetime.fromisoformat(f"{since}T00:00:00+00:00")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    
    # Fix import path - use relative import
    from ..services.chat_export_parser import parse_chat_export, compute_content_hash
    
    # Parse with since filter - filtering happens in parser now
    parsed = parse_chat_export(iter(text.splitlines(True)), since=since_dt)
    
    service = ChatIngestService(db)
    inserted = 0
    skipped = 0
    seen_in_batch = set()
    seen_canonical_in_batch = set()  # Track canonical content hashes in this batch
    seen_group_content_in_batch = set()  # Track (group_id, content_hash) combinations in this batch
    
    from ..models.database import User, Group, Message, CanonicalMessage
    
    group_name = parsed["group_name"]
    group = db.query(Group).filter(Group.group_name == group_name).first()
    if not group:
        from datetime import datetime as dt
        group = Group(
            group_id=f"export::{group_name}",
            group_name=group_name,
            university="[UNK]",
            category="general",
            member_count=0,
            last_scraped=dt.utcnow(),
        )
        db.add(group)
        db.flush()
    
    # Remove duplicate since filtering - it's now done in parser
    for msg in parsed["messages"]:
        ts = msg["timestamp"]
        mid = msg["message_id"]
        
        # Skip if we've already seen this message_id in this same upload batch
        if mid in seen_in_batch:
            skipped += 1
            continue
            
        exists = db.query(Message).filter(Message.message_id == mid).first()
        if exists:
            skipped += 1
            continue
        
        user = None
        if msg.get("sender_phone"):
            user = db.query(User).filter(User.phone_number == msg["sender_phone"]).first()
        if not user:
            user = db.query(User).filter(User.display_name == msg["sender_name"]).first()
        if not user:
            user = User(
                unique_id=f"export_user::{msg.get('sender_phone') or msg['sender_name']}",
                phone_number=msg.get("sender_phone"),
                display_name=msg["sender_name"],
            )
            db.add(user)
            db.flush()
        
        # Compute dedup content hash per group
        content_hash = compute_content_hash(msg["body"])
        group_content_key = (group.id, content_hash)
        
        # Check if we've already seen this (group_id, content_hash) in this batch
        if group_content_key in seen_group_content_in_batch:
            skipped += 1
            continue
            
        # Check if this (group_id, content_hash) already exists in DB
        dup = db.query(Message).filter(
            Message.group_id == group.id,
            Message.content_hash == content_hash,
        ).first()
        if dup:
            # Update occurrence metadata
            from datetime import datetime as dt
            dup.last_seen = ts or dt.utcnow()
            dup.occurrence_count = (dup.occurrence_count or 1) + 1
            skipped += 1
            continue

        record = Message(
            message_id=mid,
            user_id=user.id,
            group_id=group.id,
            content=msg["body"],
            timestamp=ts,
            message_type="text",
            reactions=None,
            links=msg.get("links", []),
            has_media=False,
            media_info=None,
            processed=False,
            content_hash=content_hash,
            first_seen=ts,
            last_seen=ts,
            occurrence_count=1,
        )
        db.add(record)
        # Upsert canonical across all groups
        if content_hash in seen_canonical_in_batch:
            # Already processed this content hash in this batch, just update existing canonical
            canon = db.query(CanonicalMessage).filter(CanonicalMessage.content_hash == content_hash).first()
            if canon:
                canon.last_seen = ts
                canon.occurrence_total = (canon.occurrence_total or 1) + 1
                groups = set(canon.groups_seen or [])
                groups.add(group.group_name)
                canon.groups_seen = list(groups)
        else:
            # First time seeing this content hash in this batch
            canon = db.query(CanonicalMessage).filter(CanonicalMessage.content_hash == content_hash).first()
            if canon:
                # Update existing canonical from previous batches
                canon.last_seen = ts
                canon.occurrence_total = (canon.occurrence_total or 1) + 1
                groups = set(canon.groups_seen or [])
                groups.add(group.group_name)
                canon.groups_seen = list(groups)
            else:
                # Create new canonical entry
                canon = CanonicalMessage(
                    content_hash=content_hash,
                    content=msg["body"],
                    first_seen=ts,
                    last_seen=ts,
                    occurrence_total=1,
                    groups_seen=[group.group_name],
                )
                db.add(canon)
            seen_canonical_in_batch.add(content_hash)
        inserted += 1
        seen_in_batch.add(mid)
        seen_group_content_in_batch.add(group_content_key)
    
    db.commit()
    return {"group": group.group_name, "inserted": inserted, "skipped": skipped}