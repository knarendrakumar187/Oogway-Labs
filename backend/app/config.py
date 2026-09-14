import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM Provider Configuration ("ollama", "openai", "anthropic", "mock")
    LLM_PROVIDER: str = "ollama"
    
    # Ollama settings (laptop local inference default)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_TIMEOUT_SECONDS: float = 45.0
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Anthropic settings
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Database configuration
    DATABASE_URL: str = "postgresql://lenny:growth@localhost:5432/lenny_growth"
    SQLITE_FALLBACK_URL: str = "sqlite:///./data/lenny_growth.db"
    
    # RAG parameters
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD: float = 0.30
    TOP_K_CHUNKS: int = 4
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    CHUNKS_FILE: str = os.path.join(DATA_DIR, "chunks.json")

settings = Settings()
