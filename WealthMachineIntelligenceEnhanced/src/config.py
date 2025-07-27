"""Centralised application settings.

This module uses Pydantic's `BaseSettings` to load configuration from the
environment.  These settings can be overridden via environment variables or a
.env file at runtime.
"""
from __future__ import annotations

from functools import lru_cache
from pydantic import BaseSettings, AnyUrl, Field


class Settings(BaseSettings):
    # Database
    database_url: AnyUrl = Field(..., env="DATABASE_URL")

    # Cache
    cache_host: str = Field(default="localhost", env="CACHE_HOST")
    cache_port: int = Field(default=6379, env="CACHE_PORT")

    # Vector store
    milvus_host: str = Field(default="localhost", env="MILVUS_HOST")
    milvus_port: int = Field(default=19530, env="MILVUS_PORT")

    # Identity provider
    auth_issuer_url: str = Field(default="", env="AUTH_ISSUER_URL")
    auth_client_id: str = Field(default="", env="AUTH_CLIENT_ID")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached settings instance.  Using an LRU cache ensures that
    environment variables are only read once.
    """
    return Settings()
