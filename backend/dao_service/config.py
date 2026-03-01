"""
Application configuration using Pydantic Settings.

Loads values from environment variables / .env file.
"""

from enum import Enum
from typing import List

from pydantic_settings import BaseSettings
from pydantic import Field


class ORMFramework(str, Enum):
    SQLALCHEMY = "sqlalchemy"
    TORTOISE = "tortoise"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:54322/postgres"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # ORM framework selection
    ORM_FRAMEWORK: ORMFramework = ORMFramework.SQLALCHEMY

    # Inter-service authentication
    SERVICE_API_KEYS: List[str] = Field(
        default=["goal-planner-key-abc", "scheduler-key-def", "observer-key-ghi"]
    )

    # Connection pool
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
