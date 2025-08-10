import argparse
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from .db.base import SessionLocal
from .services.chat_ingest import ChatIngestService


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest WhatsApp chat export into DB")
    p.add_argument("file", type=str, help="Path to WhatsApp _chat.txt export")
    p.add_argument("--since", type=str, default=None, help="ISO timestamp (UTC) to ingest strictly after")
    return p.parse_args()


def main():
    args = parse_args()
    since_dt = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since)

    db: Session = SessionLocal()
    try:
        service = ChatIngestService(db)
        res = service.ingest_export_file(args.file, since=since_dt)
        print(res)
    finally:
        db.close()


if __name__ == "__main__":
    main()
