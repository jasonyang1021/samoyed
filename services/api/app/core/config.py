from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Research Radar API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://radar:radar_dev_password@postgres:5432/research_radar"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_secure: bool = False
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5-mini"
    openai_ai_search_enabled: bool = True
    ai_provider: str = "rule_based"
    dify_base_url: str = "https://api.dify.ai/v1"
    dify_api_key: Optional[str] = None
    dify_search_api_key: Optional[str] = None
    dify_user: str = "research-radar"
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://127.0.0.1:8000/api/auth/google/callback"
    frontend_url: str = "http://127.0.0.1:3000/"
    admin_emails: str = ""

    model_config = SettingsConfigDict(env_file=(".env", "local.env"), extra="ignore")


settings = Settings()
