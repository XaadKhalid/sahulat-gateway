from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAHULAT_", frozen=True)

    health_requests_per_second: int = Field(default=10, ge=1, le=1000)
