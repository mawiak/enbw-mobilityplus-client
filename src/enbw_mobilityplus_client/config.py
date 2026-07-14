"""Configuration for EnBW mobility+ Client"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for EnBW mobility+ API client"""

    model_config = SettingsConfigDict(env_prefix="ENBW_", case_sensitive=False)

    # API configuration
    api_base_url: str | None = None
    auth_base_url: str | None = None
    client_id: str | None = None
    api_key: str | None = None
    ocp_apim_subscription_key: str | None = None


settings = Settings()
