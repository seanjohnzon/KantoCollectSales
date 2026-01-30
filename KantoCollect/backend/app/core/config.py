"""
Application configuration loaded from environment variables.

Uses pydantic-settings for type-safe configuration management.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        app_name: Name of the application.
        app_env: Environment (development, staging, production).
        debug: Enable debug mode.
        secret_key: Secret key for general encryption.
    """
    
    model_config = SettingsConfigDict(
        # Look for .env in both backend/ and project root
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = "KantoCollect"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-in-production"
    
    # Database - SQLite by default for local dev, PostgreSQL for production
    # Override in .env with: DATABASE_URL=postgresql://user:pass@localhost:5432/kantocollect
    database_url: str = "sqlite:///./kantocollect.db"

    # Inventory database (separate from core DB to avoid data mixing)
    inventory_database_url: str = "sqlite:///./inventory.db"

    # WhatNot sales database (separate from core and inventory DBs)
    whatnot_database_url: str = "sqlite:///./whatnot_sales.db"

    # WhatNot sales TEST database (for regression testing without affecting production)
    whatnot_test_database_url: str = "sqlite:///./whatnot_sales_test.db"

    # Authentication
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_key: str = "1453"  # Simple admin key for quick access
    
    # PriceCharting API
    pricecharting_api_key: Optional[str] = None
    
    # Shopify Integration
    shopify_store_url: Optional[str] = None
    shopify_api_key: Optional[str] = None
    shopify_api_secret: Optional[str] = None
    shopify_access_token: Optional[str] = None
    
    # eBay API
    ebay_app_id: Optional[str] = None
    ebay_cert_id: Optional[str] = None
    ebay_dev_id: Optional[str] = None
    ebay_oauth_token: Optional[str] = None
    
    # Claude API (Anthropic)
    anthropic_api_key: Optional[str] = None
    
    # Whatnot API
    whatnot_api_key: Optional[str] = None
    whatnot_api_secret: Optional[str] = None
    
    # Discord
    discord_bot_token: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    
    # CardMarket (Optional)
    cardmarket_app_token: Optional[str] = None
    cardmarket_app_secret: Optional[str] = None
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings singleton.
    """
    return Settings()


# Global settings instance
settings = get_settings()
