from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ApiKey
from .base import SQLAlchemyRepository
from ...core.security import encrypt_api_key


class WbApiKeyRepository(SQLAlchemyRepository[ApiKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ApiKey)

    async def get_active(self, user_id: int) -> list[ApiKey]:
        """Получить все активные ключи пользователя."""
        stmt = select(ApiKey).where(
            ApiKey.user_id == user_id, ApiKey.is_active)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_user(self, user_id: int) -> ApiKey | None:
        """Получить один активный ключ (если нужен один по умолчанию)."""
        stmt = select(ApiKey).where(
            ApiKey.user_id == user_id, ApiKey.is_active)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_title(self, user_id: int, title: str) -> ApiKey | None:
        """Получить активный ключ по названию."""
        stmt = select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.title == title,
            ApiKey.is_active,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_user_keys(self, user_id: int):
        """Деактивировать все ключи пользователя."""
        stmt = update(ApiKey).where(ApiKey.user_id ==
                                    user_id).values(is_active=False)
        await self.session.execute(stmt)

    async def add_key(self, user_id: int, key: str, title: str = "API Key") -> ApiKey:
        """Добавить ключ с шифрованием (если используешь напрямую)."""
        from ...core.security import encrypt_api_key
        encrypted = encrypt_api_key(key)
        key_model = ApiKey(user_id=user_id, title=title,
                           key_encrypted=encrypted)
        self.session.add(key_model)
        return key_model

    async def add_one(self, data: dict) -> ApiKey:
        """Добавить ключ из словаря (для использования в сервисе)."""
        key_model = ApiKey(**data)
        self.session.add(key_model)
        return key_model
