"""Application settings, populated from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = Field(default="development")

    database_url: str = Field(
        default="postgresql+asyncpg://lims:lims@localhost:5432/lims",
        description="Async SQLAlchemy URL.",
    )

    redis_url: str = Field(default="redis://localhost:6379/0")

    jwt_secret: str = Field(default="change-me-in-prod-please")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_minutes: int = Field(default=60 * 24)

    cors_origins: str = Field(default="http://localhost:3000")

    email_backend: str = Field(default="file", description="file | smtp")
    email_from: str = Field(default="noreply@lims.local")
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")

    uploads_dir: str = Field(default="./uploads")

    # 中華電信 TAS phone callout (Sprint 3d). When ``cht_api_key`` is empty
    # the phone_sender task logs the would-be call and exits, so dev can run
    # the escalation pipeline without burning real minutes.
    cht_api_key: str = Field(default="")
    cht_service_number: str = Field(default="")
    cht_base_url: str = Field(default="https://tasapi.cht.com.tw/apis/CHTIoT")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
