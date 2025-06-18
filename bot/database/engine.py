from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from bot.core.config import settings
from .models import Base


engine = create_async_engine(settings.postgres.async_url, echo=True)


async_session_maker = async_sessionmaker(
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
