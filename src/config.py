"""
Configuration Management

Centralized configuration using Pydantic Settings with environment variable support.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Odoo Configuration
    odoo_url: str = "http://localhost:8069"
    odoo_db: str = "odoo"
    odoo_username: str = ""
    odoo_password: str = ""
    odoo_timeout: int = 30

    # Google AI Configuration
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.1

    # Telegram Configuration
    telegram_bot_token: str = ""
    webhook_url: str = ""
    webhook_path: str = "/telegram/webhook"

    # Database Configuration
    database_url: str = "postgresql://agent:agent@localhost:5432/agent_system"
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30

    # Application
    debug: bool = False
    log_level: str = "INFO"
    app_name: str = "Multi-Agent Enterprise System"
    app_version: str = "0.1.0"

    @property
    def telegram_webhook_full_url(self) -> str:
        """Get full webhook URL for Telegram."""
        return f"{self.webhook_url}{self.webhook_path}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
