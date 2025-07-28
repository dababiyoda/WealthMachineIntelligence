"""
Configuration module for environment variables.
Uses Pydantic BaseSettings to load variables from the environment or .env file.
"""
from functools import lru_cache
from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Database
    database_url: str = "sqlite:///./test.db"

    # Caching (Valkey/Redis)
    redis_url: str = "redis://localhost:6379/0"

    # Vector database (Milvus)
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # Keycloak authentication
    keycloak_server_url: AnyUrl = "https://keycloak.example.com"
    keycloak_realm: str = "your-realm"
    keycloak_client_id: str = "your-client-id"
    keycloak_client_secret: str = "your-client-secret"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """Retrieve cached settings instance."""
    return Settings()

# Expose a module-level settings instance for convenience
settings = get_settings()
