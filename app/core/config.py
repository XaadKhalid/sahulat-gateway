from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAHULAT_", frozen=True)

    health_requests_per_second: int = Field(default=10, ge=1, le=1000)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAHULAT_", frozen=True, hide_input_in_errors=True
    )

    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def require_async_postgres(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql+asyncpg")
        return value
