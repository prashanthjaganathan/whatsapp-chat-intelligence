from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime

from ..db.base import get_db
from ..models.database import Message, CanonicalMessage

router = APIRouter()

@router.get("/messages")
async def search_messages(
    q: str = Query("", description="Full-text search on message content"),
    sender: Optional[str] = Query(None, description="Filter by sender display name contains"),
    after: Optional[datetime] = Query(None, description="Only messages after this UTC timestamp"),
    before: Optional[datetime] = Query(None, description="Only messages before this UTC timestamp"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Message)

    if sender:
        # Join to users only if needed
        from ..models.database import User
        query = query.join(User).filter(User.display_name.ilike(f"%{sender}%"))

    if after:
        query = query.filter(Message.timestamp > after)
    if before:
        query = query.filter(Message.timestamp < before)

    if q:
        # Use full-text search when possible, fallback to ILIKE
        # Note: Using plain to_tsquery for better ranking, sanitize q into terms
        ts_query = " & ".join([part for part in q.split() if part])
        if ts_query:
            query = query.filter(text("content_tsv @@ plainto_tsquery(:q)")).params(q=q)
        else:
            query = query.filter(Message.content.ilike(f"%{q}%"))

    query = query.order_by(Message.timestamp.desc())

    # Rank by timestamp desc as secondary; FTS rank could be added if needed
    rows: List[Message] = query.offset(offset).limit(limit).all()
    return [
        {
            "id": str(row.id),
            "message_id": row.message_id,
            "content": row.content,
            "timestamp": row.timestamp,
            "user_id": str(row.user_id) if row.user_id else None,
            "group_id": str(row.group_id) if row.group_id else None,
            "occurrence_count": row.occurrence_count,
        }
        for row in rows
    ]


@router.get("/top")
async def top_search_results(
    q: str = Query(..., min_length=1, description="Full-text query"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return top-ranked results across all groups using Postgres full-text search.
    Includes snippet and occurrence_count for quick triage.
    """
    sql = text(
        """
        SELECT m.id, m.message_id, m.content, m.timestamp, m.user_id, m.group_id,
               m.occurrence_count,
               g.group_name,
               ts_rank_cd(m.content_tsv, plainto_tsquery(:q)) AS rank,
               ts_headline('english', m.content, plainto_tsquery(:q), 'ShortWord=3, MaxFragments=2') AS snippet
        FROM messages m
        LEFT JOIN groups g ON g.id = m.group_id
        WHERE m.content_tsv @@ plainto_tsquery(:q)
        ORDER BY rank DESC, m.timestamp DESC
        LIMIT :limit OFFSET :offset
        """
    )
    res = db.execute(sql, {"q": q, "limit": limit, "offset": offset}).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "message_id": r["message_id"],
            "content": r["content"],
            "snippet": r["snippet"],
            "timestamp": r["timestamp"],
            "group_id": str(r["group_id"]) if r["group_id"] else None,
            "group_name": r["group_name"],
            "occurrence_count": r["occurrence_count"],
            "rank": float(r["rank"]) if r["rank"] is not None else None,
        }
        for r in res
    ]


@router.get("/canonical/top")
async def canonical_top(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    sql = text(
        """
        SELECT c.content_hash, c.content, c.occurrence_total, c.groups_seen,
               ts_rank_cd(to_tsvector('english', coalesce(c.content, '')), plainto_tsquery(:q)) AS rank,
               ts_headline('english', c.content, plainto_tsquery(:q), 'ShortWord=3, MaxFragments=2') AS snippet
        FROM canonical_messages c
        WHERE to_tsvector('english', coalesce(c.content, '')) @@ plainto_tsquery(:q)
        ORDER BY rank DESC
        LIMIT :limit OFFSET :offset
        """
    )
    res = db.execute(sql, {"q": q, "limit": limit, "offset": offset}).mappings().all()
    return [
        {
            "content_hash": r["content_hash"],
            "content": r["content"],
            "snippet": r["snippet"],
            "occurrence_total": r["occurrence_total"],
            "groups_seen": r["groups_seen"],
            "rank": float(r["rank"]) if r["rank"] is not None else None,
        }
        for r in res
    ]
