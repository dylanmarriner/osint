"""
Configuration management for OSINT Framework.

Supports environment-based configuration with sensible defaults.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)


class Config:
    """Base configuration class."""

    # Server configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    SERVER_WORKERS: int = int(os.getenv("SERVER_WORKERS", "4"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS configuration
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    ).split(",")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./osint_framework.db"
    )
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # Redis configuration (for caching and sessions)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    
    # API configuration
    API_TITLE: str = "OSINT Framework"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Privacy-focused OSINT investigation framework"
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "3600"))  # seconds
    
    # Investigation configuration
    MAX_INVESTIGATION_DURATION_MINUTES: int = int(
        os.getenv("MAX_INVESTIGATION_DURATION_MINUTES", "120")
    )
    MAX_CONCURRENT_INVESTIGATIONS: int = int(
        os.getenv("MAX_CONCURRENT_INVESTIGATIONS", "10")
    )
    
    # Report storage
    REPORT_STORAGE_PATH: str = os.getenv(
        "REPORT_STORAGE_PATH",
        "./reports"
    )
    
    # WebSocket configuration
    WEBSOCKET_HEARTBEAT_INTERVAL: int = int(
        os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", "30")
    )
    WEBSOCKET_MAX_MESSAGE_SIZE: int = int(
        os.getenv("WEBSOCKET_MAX_MESSAGE_SIZE", "1024000")
    )
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Security configuration
    API_KEY_HEADER: str = os.getenv("API_KEY_HEADER", "X-API-Key")
    ENABLE_AUTH: bool = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return status."""
        errors = []
        warnings = []
        
        # Validate database URL
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        # Validate CORS origins
        if not cls.CORS_ORIGINS or cls.CORS_ORIGINS == [""]:
            errors.append("CORS_ORIGINS is required")
        else:
            # Clean up empty strings
            cls.CORS_ORIGINS = [origin.strip() for origin in cls.CORS_ORIGINS if origin.strip()]
        
        # Validate server configuration
        if cls.SERVER_PORT < 1 or cls.SERVER_PORT > 65535:
            errors.append(f"SERVER_PORT must be between 1 and 65535, got {cls.SERVER_PORT}")
        
        # Validate investigation limits
        if cls.MAX_CONCURRENT_INVESTIGATIONS < 1:
            errors.append("MAX_CONCURRENT_INVESTIGATIONS must be at least 1")
        
        # Warn about debug mode
        if cls.DEBUG:
            warnings.append("DEBUG mode is enabled - not recommended for production")
        
        # Warn about Redis if disabled
        if not cls.REDIS_ENABLED:
            warnings.append("Redis is disabled - performance may be degraded")
        
        # Create report storage path if it doesn't exist
        try:
            Path(cls.REPORT_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Failed to create report storage path: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive values)."""
        sensitive_keys = {"DATABASE_URL", "REDIS_URL", "API_KEY_HEADER"}
        
        return {
            key: getattr(cls, key) if key not in sensitive_keys else "***"
            for key in dir(cls)
            if not key.startswith("_") and key.isupper()
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    DATABASE_ECHO = True


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    DATABASE_URL = "sqlite:///./test.db"
    REDIS_ENABLED = False
    RATE_LIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = "WARNING"


def get_config() -> Config:
    """Get appropriate configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    
    logger.info(f"Loaded {env} configuration")
    
    # Validate configuration
    validation = config_class.validate()
    if validation["errors"]:
        logger.error(f"Configuration validation failed: {validation['errors']}")
        raise ValueError(f"Invalid configuration: {validation['errors']}")
    
    if validation["warnings"]:
        for warning in validation["warnings"]:
            logger.warning(f"Configuration warning: {warning}")
    
    return config_class
