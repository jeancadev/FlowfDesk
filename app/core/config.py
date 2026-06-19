"""
FlowDesk Configuration — Centralized settings with validation at startup.

Uses pydantic-settings to load and validate all environment variables.
Fails fast if required configuration is missing or invalid.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Flask ---
    FLASK_ENV: str = "development"
    FLASK_DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"

    # --- PostgreSQL ---
    DATABASE_URL: str = (
        "postgresql://flowdesk:flowdesk_secret@localhost:5432/flowdesk_db"
    )

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Elasticsearch ---
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # --- Kafka ---
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # --- AWS S3 ---
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_S3_BUCKET: str = "flowdesk-attachments"
    AWS_S3_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_REGION: str = "us-east-1"

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def kafka_bootstrap_servers_list(self) -> list[str]:
        """Return Kafka servers as a list for the client."""
        return [s.strip() for s in self.KAFKA_BOOTSTRAP_SERVERS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — validates config once at startup."""
    return Settings()
