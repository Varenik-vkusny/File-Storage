from pydantic_settings import SettingsConfigDict, BaseSettings
from pydantic import computed_field


class Settings(BaseSettings):
    db_driver: str = "postgresql+asyncpg"
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    redis_host: str
    redis_port: int

    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_name: str
    s3_public_url: str

    @computed_field
    @property
    def sqlalchemy_database_url(self) -> str:
        base_url = (
            f"{self.db_driver}://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

        return base_url

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def get_settings():
    return Settings()
