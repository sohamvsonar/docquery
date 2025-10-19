"""
Configuration management using Pydantic Settings.
All settings are loaded from environment variables with defaults from .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
import sys

# Configure Tesseract path for Windows
if sys.platform == "win32":
    try:
        import pytesseract
        # Common Tesseract installation paths on Windows
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]

        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
    except ImportError:
        pass  # pytesseract not installed yet


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Info
    app_name: str = "DocQuery"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Database Configuration
    database_url: str

    # Redis Configuration
    redis_url: str

    # JWT Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OpenAI API
    openai_api_key: str

    # File Upload Settings
    upload_dir: str = "/app/uploads"
    max_upload_size: int = 52428800  # 50MB

    # Rate Limiting
    login_rate_limit: int = 5  # Max attempts per minute per IP

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
