import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Service identity
    SERVICE_NAME: str = "Pattern Observer Agent"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_DESCRIPTION: str = (
        "Background service that learns from user behavioral history "
        "to improve scheduling recommendations (SCRUM-50)."
    )
    PORT: int = int(os.getenv("PATTERN_OBSERVER_PORT", 8058))

    # Database (inherited from dao_service)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # OpenAI / GPT-4o-mini
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Pattern analysis thresholds
    MIN_DATA_POINTS: int = int(os.getenv("MIN_DATA_POINTS", 3))
    AVOIDANCE_MISS_THRESHOLD: int = int(os.getenv("AVOIDANCE_MISS_THRESHOLD", 3))
    AVOIDANCE_WEEK_SPAN: int = int(os.getenv("AVOIDANCE_WEEK_SPAN", 3))
    LOW_CONFIDENCE_WEEKS: int = int(os.getenv("LOW_CONFIDENCE_WEEKS", 2))
    SLOT_TOLERANCE_HOURS: int = int(os.getenv("SLOT_TOLERANCE_HOURS", 1))
    TASK_HISTORY_DAYS: int = int(os.getenv("TASK_HISTORY_DAYS", 90))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
