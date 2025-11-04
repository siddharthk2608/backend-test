# config.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    google_api_key: str  # Changed from anthropic_api_key
    
    # Application settings
    app_name: str = "Tax Return PDF Processor"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    
    # File upload settings
    max_file_size_mb: int = 50
    allowed_extensions: list = [".pdf"]
    
    # LLM settings
    llm_model: str = "gemini-2.5-flash"  # Changed from claude model
    llm_max_tokens: int = 8192  # Gemini supports higher token counts
    llm_temperature: float = 0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


