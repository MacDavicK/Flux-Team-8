"""
Flux Conv Agent -- Configuration

Reads environment variables and exposes them as typed settings.
All Deepgram, voice session, and DAO service settings live here.
"""

from pydantic_settings import BaseSettings


class ConvAgentSettings(BaseSettings):
    # Deepgram Voice Agent
    deepgram_api_key: str = ""
    deepgram_voice_model: str = "aura-2-thalia-en"
    deepgram_listen_model: str = "nova-3"
    deepgram_llm_model: str = "gpt-4o-mini"
    deepgram_token_ttl: int = 3600                  # Temp token TTL in seconds (max 1hr)
    voice_prompt_file: str = "backend/conv_agent/config/voice_prompt.md"
    voice_intents_file: str = "backend/conv_agent/config/intents.yaml"
    voice_daily_session_limit: int = 20

    # DAO Service (inter-service communication)
    dao_service_url: str = "http://localhost:8001"
    dao_service_key: str = "goal-planner-key-abc"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = ConvAgentSettings()
