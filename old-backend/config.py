from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenRouter (chat; single API key for all LLM/embedding calls)
    open_router_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "openai/gpt-4o-mini"  # OpenRouter model id
    
    # Supabase Database Configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    database_url: str = "postgresql://user:password@localhost:5432/flux"
    
    # Application Settings
    app_name: str = "Flux Agentic AI"
    debug: bool = True
    log_level: str = "INFO"
    
    # Calendar Settings
    default_work_start_hour: int = 9
    default_work_end_hour: int = 18
    default_task_duration_minutes: int = 30
    
    # Notification Settings
    notification_check_interval_minutes: int = 15
    missed_task_reschedule_days: int = 1
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()
