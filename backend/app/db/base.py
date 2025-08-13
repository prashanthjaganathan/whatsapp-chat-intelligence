from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# Build engine with safer defaults for serverless
db_url = settings.DATABASE_URL
url_obj = make_url(db_url)
connect_args = {}

# Enforce SSL for non-local Postgres if not already specified in URL
if url_obj.drivername.startswith("postgresql"):
    host = (url_obj.host or "").lower()
    if host not in ("localhost", "127.0.0.1") and "sslmode=" not in str(db_url):
        connect_args["sslmode"] = "require"

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    connect_args=connect_args or None,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()