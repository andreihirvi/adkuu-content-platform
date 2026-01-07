"""
Application configuration using Pydantic Settings.
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Info
    PROJECT_NAME: str = "Adkuu Content Platform"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "Reddit-first organic content advertising platform"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    POSTGRES_USER: str = "reddit_platform"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "reddit_platform"
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v, info):
        if v:
            return v
        values = info.data
        return (
            f"postgresql://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@"
            f"{values.get('POSTGRES_HOST')}:"
            f"{values.get('POSTGRES_PORT')}/"
            f"{values.get('POSTGRES_DB')}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_url(cls, v, info):
        if v:
            return v
        values = info.data
        password = values.get('REDIS_PASSWORD')
        if password:
            return f"redis://:{password}@{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
        return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v, info):
        if v:
            return v
        values = info.data
        password = values.get('REDIS_PASSWORD')
        if password:
            return f"redis://:{password}@{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/1"
        return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/1"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v, info):
        if v:
            return v
        values = info.data
        password = values.get('REDIS_PASSWORD')
        if password:
            return f"redis://:{password}@{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/2"
        return f"redis://{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/2"

    # Reddit OAuth
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_REDIRECT_URI: str = "http://localhost:8000/api/v1/reddit/auth/callback"
    REDDIT_USER_AGENT: str = "reddit-content-platform:v1.0.0"

    # Frontend URL (for OAuth redirects)
    FRONTEND_URL: str = "http://localhost:3000"

    # LLM APIs
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Default LLM settings
    DEFAULT_LLM_MODEL: str = "gpt-4o"  # Best for complex, high-quality content
    DEFAULT_LLM_MODEL_FAST: str = "gpt-4o-mini"  # For simpler tasks and fallback
    DEFAULT_LLM_TEMPERATURE: float = 0.8  # Slightly higher for more natural variation
    DEFAULT_LLM_MAX_TOKENS: int = 800  # Concise is better for Reddit

    # Security
    SECRET_KEY: str = "change_this_to_a_secure_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ENCRYPTION_KEY: str = ""  # Fernet key for token encryption

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://content.adkuu.net",
        "https://backoffice-adkuu.vercel.app",
        "https://*.vercel.app",
    ]

    # Tracking (optional)
    TRACKING_BASE_URL: Optional[str] = None

    # Mining Settings
    MINING_INTERVAL_MINUTES: int = 15
    MAX_OPPORTUNITIES_PER_MINE: int = 100
    OPPORTUNITY_EXPIRY_HOURS: int = 24

    # Content Generation Settings
    MAX_CONTENT_LENGTH: int = 2000
    MIN_CONTENT_LENGTH: int = 50

    # Rate Limiting
    REDDIT_MIN_ACTION_INTERVAL_SECONDS: int = 60  # Min seconds between Reddit actions
    MAX_DAILY_POSTS_PER_ACCOUNT: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
