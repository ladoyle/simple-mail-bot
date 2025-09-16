import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HOST_URL: str
    PORT: int
    ORIGIN: str
    SSL_KEY_PATH: str
    SSL_CERT_PATH: str

    APP_RELOAD: bool
    DEBUG: bool

    GMAIL_REDIRECT_URI: str

    model_config = SettingsConfigDict(env_file=f'.env.{os.getenv("APP_ENV", "local")}', env_file_encoding="utf-8")


settings = Settings()
