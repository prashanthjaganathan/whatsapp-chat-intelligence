from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from .core.config import settings
from .db.base import Base, engine
from .db.search_index import ensure_postgres_full_text_search
from .api import items, apartments, search, ingest, process, bot, export

# Defer DB initialization to application startup to avoid import-time failures
def _init_db():
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        # Ensure search index
        try:
            ensure_postgres_full_text_search(engine)
        except Exception as e:
            # Non-fatal during first boot/migrations
            print(f"Search index init warning: {e}")
    except Exception as e:
        # Avoid crashing the app on environments without DB (e.g., Vercel without managed DB yet)
        print(f"Database init warning: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="University Group Chat Data Management API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Run DB initialization on startup (keeps Docker behavior, avoids import-time connect)
@app.on_event("startup")
async def on_startup():
    _init_db()

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(items.router, prefix=f"{settings.API_V1_STR}/items", tags=["items"])
app.include_router(apartments.router, prefix=f"{settings.API_V1_STR}/apartments", tags=["apartments"])
app.include_router(search.router, prefix=f"{settings.API_V1_STR}/search", tags=["search"])
app.include_router(ingest.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["ingest"])
app.include_router(process.router, prefix=f"{settings.API_V1_STR}/process", tags=["process"])
app.include_router(bot.router, prefix=f"{settings.API_V1_STR}/bot", tags=["bot"])
app.include_router(export.router, prefix=f"{settings.API_V1_STR}/export", tags=["export"])

# Also expose DB ping under the API prefix to avoid 404 when only prefixed routes are used
@app.get(f"{settings.API_V1_STR}/db/ping")
async def db_ping_prefixed():
    return await db_ping()

@app.get("/")
async def root():
    return {
        "message": "University Group Chat Data Management API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

@app.get("/db/ping")
async def db_ping():
    try:
        with engine.connect() as conn:
            ver = conn.execute(text("select version()"))
            version = ver.scalar() or "unknown"
        url = engine.url
        safe = {
            "driver": url.drivername,
            "host": url.host,
            "port": url.port,
            "database": url.database,
        }
        return {"ok": True, "db": safe, "version": version}
    except Exception as e:
        return {"ok": False, "error": str(e)}