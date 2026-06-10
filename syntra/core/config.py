from functools import lru_cache
import os
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
    github_app_id: str | None = Field(default=None, alias="GITHUB_APP_ID")
    github_app_private_key_path: str | None = Field(
        default=None, alias="GITHUB_APP_PRIVATE_KEY_PATH"
    )
    github_app_webhook_secret: str | None = Field(default=None, alias="GITHUB_APP_WEBHOOK_SECRET")
    github_app_slug: str | None = Field(default=None, alias="GITHUB_APP_SLUG")
    slack_client_id: str | None = Field(default=None, alias="SLACK_CLIENT_ID")
    slack_client_secret: str | None = Field(default=None, alias="SLACK_CLIENT_SECRET")
    encryption_key: str | None = Field(default=None, alias="ENCRYPTION_KEY")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str | None = Field(default=None, alias="STRIPE_PUBLISHABLE_KEY")
    cron_secret: str | None = Field(default=None, alias="CRON_SECRET")
    auto_create_db: bool = Field(default=True, alias="AUTO_CREATE_DB")
    workspace_dir: Path = Field(default=Path("./workspace"), alias="WORKSPACE_DIR")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if os.getenv("VERCEL"):
        settings.auto_create_db = False
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    return settings
