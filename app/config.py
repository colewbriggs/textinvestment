"""Application configuration from environment variables."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment."""

    # Twilio
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Alpha Vantage
    alpha_vantage_api_key: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./investor.db")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Application
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
