from datetime import timedelta

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAHULAT_", frozen=True, hide_input_in_errors=True
    )

    admin_session_cookie: str = Field(default="session", min_length=1, max_length=100)
    admin_session_ttl_seconds: int = Field(default=8 * 3600, ge=60, le=30 * 24 * 3600)


def session_ttl(settings: AdminSettings) -> timedelta:
    return timedelta(seconds=settings.admin_session_ttl_seconds)
