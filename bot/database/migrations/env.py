import sys
from bot.core.config import settings
from bot.database.models import Base
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).resolve().parents[2]))


# Alembic Config
config = context.config
fileConfig(config.config_file_name)

# Прокидываем URL подключения из pydantic настроек
config.set_main_option(
    "sqlalchemy.url", settings.postgres.async_url + "?async_fallback=True")

target_metadata = Base.metadata


def run_migrations_offline():
    """Запуск миграций в оффлайн-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        timezone="utc",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Запуск миграций в онлайн-режиме."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            timezone="utc",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
