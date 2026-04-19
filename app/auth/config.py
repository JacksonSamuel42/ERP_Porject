from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    JWT_ALG: str
    JWT_SECRET: str
    JWT_EXP_SECONDS: int = 900  # 15m

    REFRESH_TOKEN_KEY: str
    REFRESH_TOKEN_EXP_SECONDS: int = 2592000  # 30d

    SECURE_COOKIES: bool = True

    @property
    def JWT_EXP(self) -> timedelta:
        return timedelta(seconds=self.JWT_EXP_SECONDS)

    @property
    def REFRESH_TOKEN_EXP(self) -> timedelta:
        return timedelta(seconds=self.REFRESH_TOKEN_EXP_SECONDS)

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )


auth_settings = Settings()
