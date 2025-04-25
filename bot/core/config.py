from pydantic_settings import BaseSettings
from pydantic import SecretStr


class PostgresSettings(BaseSettings):
    user: str
    password: SecretStr
    db: str
    host: str = "db"
    port: int = 5432

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    url: str = "redis://redis:6379/0"


class NatsSettings(BaseSettings):
    url: str = "nats://nats:4223"


class BotSettings(BaseSettings):
    token: SecretStr
    admin_id: int
    locale_path: str = "./locales"


class AppSettings(BaseSettings):
    fernet_secret: SecretStr
    trial_days: int = 14  # длительность пробного периода в днях

    postgres: PostgresSettings
    redis: RedisSettings
    nats: NatsSettings
    bot: BotSettings

    class Config:
        env_file = ".env"
        env_nested_delimiter = '__'


settings = AppSettings()
