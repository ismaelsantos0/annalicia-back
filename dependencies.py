from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    admin_username: str = "master"
    admin_password: str = "admin123"
    cors_origins: list[str] = ["*"]
    
    # Evolution API (WhatsApp)
    evolution_api_url: str = ""
    evolution_api_key: str = ""
    evolution_instance: str = ""
    admin_phone: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
