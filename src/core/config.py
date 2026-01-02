from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    HYPERLIQUID_WALLET_ADDRESS: Optional[str] = None
    
    OKX_API_KEY: Optional[str] = None
    OKX_SECRET: Optional[str] = None
    OKX_PASSWORD: Optional[str] = None
    
    DELTA_API_KEY: Optional[str] = None
    DELTA_SECRET: Optional[str] = None

    DATABASE_URL: str = "sqlite+aiosqlite:///./portfolio.db"
    
    OPENAI_API_KEY: Optional[str] = None

settings = Settings()
