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

    # AI / LLM — OpenRouter (chat + embeddings; single API key)
    open_router_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "openai/gpt-4o-mini"  # OpenRouter model id
    embedding_model: str = "openai/text-embedding-3-small"

    # RAG — Pinecone (vector store)
    pinecone_api_key: str = ""
    pinecone_index_name: str = "flux-articles"

    # RAG — Chunking & retrieval
    rag_chunk_size: int = 2000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 5
    rag_relevance_threshold: float = 0.2

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
