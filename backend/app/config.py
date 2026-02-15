"""
Flux Backend — Application Configuration

Reads environment variables from .env and exposes them as typed settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/flux"
    supabase_url: str = "http://127.0.0.1:54321"
    supabase_key: str = ""

    # AI / LLM
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # CORS — allowed origins for the frontend
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
