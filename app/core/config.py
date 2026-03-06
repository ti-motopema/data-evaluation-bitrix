from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Bitrix Webhook API"
    DEBUG: bool = True
    BITRIX_WEBHOOK_URL: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()