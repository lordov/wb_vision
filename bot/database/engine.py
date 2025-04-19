from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from datetime import datetime

from bot.core.config import settings


class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(
        DateTime(), default=datetime.now)
    updated: Mapped[DateTime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now)


engine = create_async_engine(settings.database_url, echo=True)


session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

if __name__ == '__main__':
    print(f'{__name__} Запущен самостоятельно')
else:
    print(f'{__name__} Запущен как модуль')
