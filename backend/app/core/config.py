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
    jwt_access_expires_minutes: int = Field(default=60)
    jwt_refresh_expires_days: int = Field(default=7)

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

    # TAS MQTT listener (call-pickup-as-acknowledgement). When ``tas_enabled``
    # is False the listener entrypoint exits immediately and the REST callout
    # short-circuits to a no-op — keeps CI / local dev from dialling real
    # numbers when credentials aren't provisioned. ``tas_sn_key`` keys the
    # MQTT topic ``phone-conn/calloutResult/${SN_KEY}``; broker URL defaults
    # to the production TLS endpoint.
    tas_enabled: bool = Field(default=False)
    tas_sn_key: str = Field(default="")
    tas_mqtt_broker_url: str = Field(default="tls://tasapi.cht.com.tw:2883")

    # Demo / dev: when set, seed_dev.py writes this number into every
    # User.phone so the CHT callout pipeline can be exercised end-to-end
    # without per-account phone management. Empty = phone column left NULL
    # for all seeded users and phone fan-out becomes a no-op.
    demo_phone: str = Field(default="")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
