from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RSA_PRIVATE_KEY: str

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )


license_settings = Settings()
