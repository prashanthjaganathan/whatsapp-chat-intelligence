from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..models.database import User, Group, Message, CanonicalMessage
from .chat_export_parser import parse_chat_export, compute_content_hash

class ChatIngestService:
    def __init__(self, db: Session):
        self.db = db

    def ingest_export_file(self, file_path: str, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Ingest a WhatsApp exported chat text file into relational DB.
        - Creates Group if missing using group name
        - Creates/updates Users by phone if present, else by display_name as soft identifier
        - Deduplicates messages by deterministic message_id
        - Supports incremental ingest via `since` (UTC)
        """
        results = {"group": None, "inserted": 0, "skipped": 0}
        seen_in_batch = set()
        seen_canonical_in_batch = set()  # Track canonical content hashes in this batch
        seen_group_content_in_batch = set()  # Track (group_id, content_hash) combinations in this batch

        with open(file_path, "r", encoding="utf-8") as f:
            parsed = parse_chat_export(iter(f))

        group_name = parsed["group_name"]
        group = self.db.query(Group).filter(Group.group_name == group_name).first()
        if not group:
            group = Group(
                group_id=f"export::{group_name}",
                group_name=group_name,
                university="Unknown",
                category="general",
                member_count=0,
                last_scraped=datetime.utcnow(),
            )
            self.db.add(group)
            self.db.flush()
        results["group"] = group.group_name

        # Normalize `since` to UTC-aware if provided naive
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        for msg in parsed["messages"]:
            timestamp: datetime = msg["timestamp"]
            if since and timestamp <= since:
                results["skipped"] += 1
                continue

            mid = msg["message_id"]
            if mid in seen_in_batch:
                results["skipped"] += 1
                continue

            existing = self.db.query(Message).filter(Message.message_id == mid).first()
            if existing:
                results["skipped"] += 1
                continue

            # Upsert user
            user = None
            if msg.get("sender_phone"):
                user = self.db.query(User).filter(User.phone_number == msg["sender_phone"]).first()
            if not user:
                # fallback by display name
                user = self.db.query(User).filter(User.display_name == msg["sender_name"]).first()
            if not user:
                user = User(
                    unique_id=f"export_user::{msg.get('sender_phone') or msg['sender_name']}",
                    phone_number=msg.get("sender_phone"),
                    display_name=msg["sender_name"],
                )
                self.db.add(user)
                self.db.flush()

            # Deduplicate by normalized content hash per group
            content_hash = compute_content_hash(msg["body"])
            group_content_key = (group.id, content_hash)
            
            # Check if we've already seen this (group_id, content_hash) in this batch
            if group_content_key in seen_group_content_in_batch:
                results["skipped"] += 1
                continue
                
            # Check if this (group_id, content_hash) already exists in DB
            dup = self.db.query(Message).filter(
                Message.group_id == group.id,
                Message.content_hash == content_hash,
            ).first()
            if dup:
                dup.last_seen = timestamp
                dup.occurrence_count = (dup.occurrence_count or 1) + 1
                results["skipped"] += 1
                continue

            record = Message(
                message_id=mid,
                user_id=user.id,
                group_id=group.id,
                content=msg["body"],
                timestamp=timestamp,
                message_type="text",
                reactions=None,
                links=msg.get("links", []),
                has_media=False,
                media_info=None,
                processed=False,
                content_hash=content_hash,
                first_seen=timestamp,
                last_seen=timestamp,
                occurrence_count=1,
            )
            self.db.add(record)
            # Upsert canonical across all groups
            if content_hash in seen_canonical_in_batch:
                # Already processed this content hash in this batch, just update existing canonical
                canon = self.db.query(CanonicalMessage).filter(CanonicalMessage.content_hash == content_hash).first()
                if canon:
                    canon.last_seen = timestamp
                    canon.occurrence_total = (canon.occurrence_total or 1) + 1
                    groups = set(canon.groups_seen or [])
                    groups.add(group.group_name)
                    canon.groups_seen = list(groups)
            else:
                # First time seeing this content hash in this batch
                canon = self.db.query(CanonicalMessage).filter(CanonicalMessage.content_hash == content_hash).first()
                if canon:
                    # Update existing canonical from previous batches
                    canon.last_seen = timestamp
                    canon.occurrence_total = (canon.occurrence_total or 1) + 1
                    groups = set(canon.groups_seen or [])
                    groups.add(group.group_name)
                    canon.groups_seen = list(groups)
                else:
                    # Create new canonical entry
                    canon = CanonicalMessage(
                        content_hash=content_hash,
                        content=msg["body"],
                        first_seen=timestamp,
                        last_seen=timestamp,
                        occurrence_total=1,
                        groups_seen=[group.group_name],
                    )
                    self.db.add(canon)
                seen_canonical_in_batch.add(content_hash)
            results["inserted"] += 1
            seen_in_batch.add(mid)
            seen_group_content_in_batch.add(group_content_key)

        self.db.commit()
        return results
