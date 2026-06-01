from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    github_token: str = Field(alias="GITHUB_TOKEN")
    slack_bot_token: str = Field(alias="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(alias="SLACK_SIGNING_SECRET")
    slack_app_token: str = Field(alias="SLACK_APP_TOKEN")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    workspace_dir: Path = Field(default=Path("./workspace"), alias="WORKSPACE_DIR")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    return settings
