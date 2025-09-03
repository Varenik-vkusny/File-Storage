from pydantic_settings import SettingsConfigDict, BaseSettings
from pydantic import computed_field


class Settings(BaseSettings):
    db_driver: str='postgresql+asyncpg'
    db_user: str | None=None
    db_password: str | None=None
    db_host: str | None=None
    db_port: int | None=None
    db_name: str | None=None
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    @computed_field
    @property
    def sqlalchemy_database_url(self) -> str:
        return f'{self.db_driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'
    
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    

def get_settings():
    return Settings()