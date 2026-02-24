"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Central configuration for the YouTube RAG application."""

    # --- Ollama ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    AVAILABLE_MODELS: List[str] = ["tinyllama", "phi3:mini"]
    DEFAULT_MODEL: str = "tinyllama"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # --- RAG Parameters ---
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 80
    DEFAULT_TOP_K: int = 4
    DEFAULT_TEMPERATURE: float = 0.1

    # --- Observability & Security ---
    LOG_LEVEL: str = "INFO"
    ENABLE_EVALUATION: bool = True
    MAX_VIDEO_LENGTH_SEC: int = 7200  # 2 hours limit for safety
    
    # --- CORS ---
    CORS_ORIGINS: List[str] = ["*"]

    # --- Server ---
    APP_TITLE: str = "YouTube RAG"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
