"""
AI Super App - Configuration
"""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    APP_NAME: str = "AI Super App"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    STABILITY_API_KEY: Optional[str] = None

    DATABASE_URL: str = "sqlite:///./ai_super_app.db"
    REDIS_URL: str = "redis://localhost:6379"

    VPN_ENABLED: bool = True
    PROXY_LIST: List[str] = []
    PROXY_ROTATION_INTERVAL: int = 5

    DEFAULT_MODEL: str = "auto"
    FALLBACK_MODELS: List[str] = ["gpt-4", "claude-3", "gemini-pro", "llama-3"]

    OFFLINE_MODEL_PATH: str = "./models"
    ENABLE_OFFLINE: bool = True

    RATE_LIMIT_PER_MINUTE: int = 60

    SECRET_KEY: str = "super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ADMIN_USERNAME: str = "admin@1234"
    ADMIN_PASSWORD: str = "asd12345"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
