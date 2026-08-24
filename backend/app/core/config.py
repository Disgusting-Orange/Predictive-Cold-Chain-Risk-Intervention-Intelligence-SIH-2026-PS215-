import os
from pydantic_settings import BaseSettings
from typing import List, Union


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Cold Chain Optimisation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./coldchain.db"
    )
    DATABASE_SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL",
        "sqlite:///./coldchain.db"
    )
    
    JWT_SECRET: str = os.getenv("JWT_SECRET", "sih2026_coldchain_secret_key_998877665544332211")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    RISK_ENGINE_MODE: str = os.getenv("RISK_ENGINE_MODE", "heuristic")
    
    PUBLIC_URL: str = os.getenv("PUBLIC_URL", "https://ambitious-divided-catsup.ngrok-free.dev")
    NGROK_URL: str = os.getenv("NGROK_URL", "https://ambitious-divided-catsup.ngrok-free.dev")
    
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://coldchaiai-dffrzqpg.manus.space",
        "https://ambitious-divided-catsup.ngrok-free.dev",
        "*"
    ]

    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

if isinstance(settings.CORS_ORIGINS, str):
    settings.CORS_ORIGINS = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
