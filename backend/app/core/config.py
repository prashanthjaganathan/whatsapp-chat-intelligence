from pydantic_settings import BaseSettings
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
    
    # Search
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    
    # Processing Settings
    PROCESSING_BATCH_SIZE: int = 50
    LLM_RATE_LIMIT_DELAY: float = 1.0
    MAX_RETRIES: int = 3
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()