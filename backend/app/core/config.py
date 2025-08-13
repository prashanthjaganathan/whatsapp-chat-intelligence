from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import secrets

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "University Chat Manager"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/university_chat"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM APIs
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    # Accept optional Gemini key if present
    GEMINI_API_KEY: Optional[str] = None
    
    # Search
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    
    # Processing Settings
    PROCESSING_BATCH_SIZE: int = 50
    LLM_RATE_LIMIT_DELAY: float = 1.0
    MAX_RETRIES: int = 3

    # WhatsApp-related settings (optional; scraper runs outside Vercel)
    WHATSAPP_SESSION_PATH: Optional[str] = None
    WHATSAPP_TIMEOUT: Optional[int] = None
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # ignore unexpected env vars (e.g., GEMINI_API_KEY, WhatsApp vars)
    )

settings = Settings()