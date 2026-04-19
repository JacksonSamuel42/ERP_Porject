from pathlib import Path

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import Environment


class Settings(BaseSettings):
    DATABASE_URL: PostgresDsn
    ENVIRONMENT: Environment = Environment.PRODUCTION

    S3_BUCKET_NAME: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_REGION: str
    S3_ENDPOINT_URL: str

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str
    MAIL_FROM_NAME: str = 'Project G'
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    TEMPLATE_FOLDER: Path = Path(__file__).parent.parent / 'templates' / 'email'

    FRONTEND_URL: str = 'https://meuerp.ao'
    APP_VERSION: str = '1.0'

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )


settings = Settings()
