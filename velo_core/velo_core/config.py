import os
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    whisper_model: str = "base"
    porcupine_access_key: str = ""
    chrome_debug_port: int = 9222
    log_level: str = "DEBUG"
    host: str = "0.0.0.0"
    port: int = 8000
    playwright_browsers_path: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore unknown .env keys


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Apply playwright browser path to env so Playwright picks it up
    if settings.playwright_browsers_path:
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", settings.playwright_browsers_path)
    return settings