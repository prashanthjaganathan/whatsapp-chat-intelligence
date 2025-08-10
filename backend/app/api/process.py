from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db.base import get_db
from ..services.entity_extractor import EntityExtractor
from ..models.database import Message, CanonicalMessage
from ..services.chat_export_parser import compute_content_hash

router = APIRouter()

@router.post("/run")
async def run_processing(
    use_llm: bool = Query(False, description="Use LLM for extraction if keys configured"),
    batch: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    extractor = EntityExtractor(db, use_llm=use_llm)
    stats = await extractor.process_unprocessed(limit=batch)
    return stats


@router.post("/backfill-canonical")
async def backfill_canonical(
    limit: int = Query(2000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Backfill canonical_messages from existing messages across all groups."""
    rows = db.query(Message).order_by(Message.timestamp.desc()).limit(limit).all()
    upserted = 0
    for r in rows:
        ch = r.content_hash or compute_content_hash(r.content or "")
        canon = db.query(CanonicalMessage).filter(CanonicalMessage.content_hash == ch).first()
        if canon:
            canon.last_seen = r.timestamp or canon.last_seen
            canon.occurrence_total = (canon.occurrence_total or 1) + 1
            groups = set(canon.groups_seen or [])
            # we don't have group name here; cheap fallback to group_id string
            groups.add(str(r.group_id) if r.group_id else "unknown")
            canon.groups_seen = list(groups)
        else:
            canon = CanonicalMessage(
                content_hash=ch,
                content=r.content,
                first_seen=r.timestamp,
                last_seen=r.timestamp,
                occurrence_total=1,
                groups_seen=[str(r.group_id) if r.group_id else "unknown"],
            )
            db.add(canon)
            upserted += 1
    db.commit()
    return {"upserted": upserted}
