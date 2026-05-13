from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = Field(alias="APP_NAME")
    app_env: str = Field(alias="APP_ENV")
    debug: bool = Field(alias="DEBUG")

    database_url:str = Field(alias="DATABASE_URL")
    redis_url:str = Field(alias="REDIS_URL")
    celery_broker_url:str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend:str = Field(alias="CELERY_RESULT_BACKEND")

    mcp_readonly: bool = Field(default=True, alias="MCP_READONLY")
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()