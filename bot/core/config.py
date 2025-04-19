from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    bot_token: SecretStr
    fernet_secret: SecretStr

    postgres_pass: SecretStr
    postgres_user: str
    postgres_db: str

    database_url: str
    redis_url: str
    nats_url: str
    
    admin_id: int

    locale_path: str = "./locales"

    class Config:
        env_file = ".env"

settings = Settings()