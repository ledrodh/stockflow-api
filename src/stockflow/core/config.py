"""Application configuration managed via pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_INSECURE_SECRET_KEY = "stockflow-dev-secret-jwt-key-safe-for-local-dev-only-2026"
DEFAULT_INSECURE_POSTGRES_PASSWORD = "stockflow_secret_password"


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

    # CORS Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database
    POSTGRES_USER: str = "stockflow"
    POSTGRES_PASSWORD: str = DEFAULT_INSECURE_POSTGRES_PASSWORD
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = Field(default=5432, ge=1, le=65535)
    POSTGRES_DB: str = "stockflow_db"
    DATABASE_URL: str | None = None

    # Security & JWT
    SECRET_KEY: str = Field(
        default=DEFAULT_INSECURE_SECRET_KEY,
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, le=1440)

    # Concurrency & Idempotency
    DB_LOCK_TIMEOUT_MS: int = Field(default=5000, ge=100, le=60000)
    IDEMPOTENCY_TTL_HOURS: int = Field(default=24, ge=1, le=720)

    # Operations & Seeding
    ENABLE_DEMO_SEED: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_no_sqlite(cls, value: str | None) -> str | None:
        """Ensure SQLite is never used, enforcing PostgreSQL-only execution."""
        if value and "sqlite" in value.lower():
            raise ValueError("SQLite is strictly prohibited. StockFlow API requires PostgreSQL.")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Disallow default development credentials and keys in production environments."""
        if self.APP_ENV == "production":
            if self.SECRET_KEY == DEFAULT_INSECURE_SECRET_KEY:
                raise ValueError(
                    "In production, SECRET_KEY must be set to a secure, randomly generated "
                    "secret via environment variable and cannot use the development default."
                )
            if self.POSTGRES_PASSWORD == DEFAULT_INSECURE_POSTGRES_PASSWORD:
                raise ValueError(
                    "In production, POSTGRES_PASSWORD must be configured securely and "
                    "cannot use the default development password."
                )
        return self

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
