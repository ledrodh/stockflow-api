"""Application configuration managed via pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "StockFlow API"
    APP_ENV: str = Field(
        default="development",
        pattern=r"^(development|testing|staging|production)$",
    )
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    POSTGRES_USER: str = "stockflow"
    POSTGRES_PASSWORD: str = "stockflow_secret_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str = "stockflow_db"
    DATABASE_URL: str | None = None

    # Security & JWT
    SECRET_KEY: str = Field(
        default="stockflow-dev-secret-jwt-key-safe-for-local-dev-only-2026",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)

    # Concurrency & Idempotency
    DB_LOCK_TIMEOUT_MS: int = Field(default=5000, ge=100, le=60000)
    IDEMPOTENCY_TTL_HOURS: int = Field(default=24, ge=1, le=720)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_no_sqlite(cls, value: str | None) -> str | None:
        """Ensure SQLite is never used, enforcing PostgreSQL-only execution."""
        if value and "sqlite" in value.lower():
            raise ValueError("SQLite is strictly prohibited. StockFlow API requires PostgreSQL.")
        return value

    @property
    def async_database_url(self) -> str:
        """Return the asyncpg SQLAlchemy database URL."""
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Return the psycopg3 synchronous SQLAlchemy database URL (useful for Alembic CLI)."""
        return self.async_database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


settings = get_settings()
