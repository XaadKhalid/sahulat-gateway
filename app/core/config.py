from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAHULAT_", frozen=True)

    health_requests_per_second: int = Field(default=10, ge=1, le=1000)
    webhook_requests_per_second: int = Field(default=100, ge=1, le=10000)
    webhook_secret: SecretStr
    webhook_verify_token: SecretStr


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


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SAHULAT_", frozen=True, hide_input_in_errors=True
    )

    redis_url: SecretStr

    @field_validator("redis_url")
    @classmethod
    def require_redis(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("redis://"):
            raise ValueError("Redis URL must use redis://")
        return value
