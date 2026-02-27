from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_env: str = "development"
    secret_key: str
    log_level: str = "INFO"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str  # asyncpg direct connection

    # LLMs — all via OpenRouter
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "Flux"
    openrouter_app_url: str = ""

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str
    langchain_project: str = "flux-development"

    # Sentry
    sentry_dsn: str
    sentry_traces_sample_rate: float = 0.2
    sentry_environment: str = "development"

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    twilio_voice_from: str
    twilio_verify_service_sid: str
    twilio_webhook_base_url: str

    # Web Push
    vapid_private_key: str
    vapid_public_key: str
    vapid_claims_email: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Notification defaults
    reminder_lead_minutes: int = 10
    escalation_window_minutes: int = 2
    notification_poll_interval_seconds: int = 60

    # Cost controls
    monthly_token_soft_limit: int = 500_000
    monthly_token_hard_limit: int = 1_000_000
    max_conversation_messages: int = 20
    max_conversation_tokens: int = 8_000

    # Business logic
    max_active_goals: int = 3
    goal_sprint_weeks: int = 6
    pattern_miss_threshold: int = 3
    pattern_min_datapoints: int = 3


settings = Settings()
