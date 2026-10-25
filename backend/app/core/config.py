import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "AICTE Sentinel"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return ["http://localhost:5173"]
        return v

    # Security & JWT
    SECRET_KEY: str = "sentinel-local-dev-secret-key-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentinel_dev.db"
    DATABASE_SYNC_URL: str = "sqlite:///./sentinel_dev.db"
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_DB_PATH: str = "./sentinel_dev.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_ENDPOINT: str = "localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET_QUARANTINE: str = "aicte-quarantine"
    STORAGE_BUCKET_VAULT: str = "aicte-vault"
    STORAGE_USE_SSL: bool = False

    # ClamAV Antivirus
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    # Audit & Cryptographic Verification
    AUDIT_MERKLE_SALT: str = "sentinel-merkle-secret-salt-2026"
    MERKLE_BATCH_INTERVAL_MINUTES: int = 60

    # Demo Seed
    SEED_SUPERADMIN_EMAIL: str = "superadmin@aicte-india.org"
    SEED_SUPERADMIN_PASSWORD: str = "Sentinel@Admin2026!"
    SEED_SYNTHETIC_DATA: bool = True


settings = Settings()
