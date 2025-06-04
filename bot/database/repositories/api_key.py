from sqlalchemy import delete, select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from bot.schemas.wb import ApiKeyWithTelegramDTO

from ..models import ApiKey
from .base import SQLAlchemyRepository
from ...core.logging import db_logger


class WbApiKeyRepository(SQLAlchemyRepository[ApiKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, ApiKey)

    async def get_active(self, user_id: int) -> list[ApiKey]:
        """Получить все активные ключи пользователя."""
        stmt = select(ApiKey).where(
            ApiKey.user_id == user_id, ApiKey.is_active)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_by_user(self, user_id: int, title: str) -> ApiKey | None:
        """Получить один активный ключ (если нужен один по умолчанию)."""
        stmt = select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.is_active,
            ApiKey.title == title,
        )
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

    async def delete_user_keys(self, user_id: int):
        """Удалить все ключи пользователя."""
        stmt = delete(ApiKey).where(ApiKey.user_id == user_id)
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

    async def upsert_key(
        self,
        user_id: int,
        title: str,
        encrypted_key: str,
        is_active: bool,
    ) -> None:
        """Upsert (insert or update) an API key.

        Args:
            user_id (int): ID of the user to whom the API key belongs.
            title (str): Title of the API key.
            encrypted_key (str): Encrypted API key.
            is_active (bool): Whether the API key is active.

        Returns:
            None
        """
        try:
            stmt = select(ApiKey).where(
                ApiKey.user_id == user_id,
                ApiKey.title == title,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.key_encrypted = encrypted_key
                existing.is_active = is_active
            else:
                self.session.add(ApiKey(
                    user_id=user_id,
                    title=title,
                    key_encrypted=encrypted_key,
                    is_active=is_active,
                ))
        except SQLAlchemyError as e:
            raise e

    async def get_all_keys(self) -> list[ApiKeyWithTelegramDTO]:
        stmt = select(ApiKey).options(joinedload(ApiKey.user))
        try:
            result = await self.session.execute(stmt)
            api_keys: list[ApiKey] = result.scalars().all()
        except Exception as e:
            db_logger.error(e)
            return []

        return [
            ApiKeyWithTelegramDTO(
                id=key.id,
                user_id=key.user_id,
                title=key.title,
                # Предполагается, что ты уже умеешь расшифровывать
                key_encrypted=key.key_encrypted,
                is_active=key.is_active,
                telegram_id=key.user.telegram_id if key.user else None,
            )
            for key in api_keys
        ]
