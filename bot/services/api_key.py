from cryptography.fernet import Fernet, InvalidToken

from bot.database.repositories.api_key import WbApiKeyRepository
from bot.database.models import ApiKey
from bot.database.uow import UnitOfWork
from bot.services.subscription import SubscriptionService
from ..core.logging import app_logger


class ApiKeyDecryptionError(Exception):
    pass


class ApiKeyService:
    def __init__(self, uow: UnitOfWork, fernet: Fernet):
        self.repo = uow.api_keys
        self.user_repo = uow.users
        self.fernet = fernet

    async def get_user_key_titles(self, telegram_id: int) -> list[dict]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        app_logger.info("Fetching API key titles", user_id=user.id)
        keys = await self.repo.get_active(user.id)
        return [{"id": key.id, "title": key.title} for key in keys]

    async def add_encrypt_key(self, telegram_id: int, raw_key: str, title: str = "API Key") -> ApiKey:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        app_logger.info("Encrypting and adding API key",
                        user_id=user.id, title=title)
        encrypted = self.fernet.encrypt(raw_key.encode()).decode()
        key = await self.repo.add_one({
            "user_id": user.id,
            "title": title,
            "key_encrypted": encrypted,
        })
        app_logger.info("API key added successfully", key_id=key.id)
        return key

    async def decrypt_key(self, encrypted_key: str) -> str:
        app_logger.debug("Decrypting API key")
        try:
            return self.fernet.decrypt(encrypted_key.encode()).decode()
        except InvalidToken:
            app_logger.warning("Failed to decrypt API key: invalid token")
            raise ApiKeyDecryptionError("Invalid or corrupted key")

    async def get_decrypted_by_title(self, telegram_id: int, title: str) -> str | None:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")

        app_logger.info("Getting and decrypting API key by title",
                        user_id=user.id, title=title)
        key = await self.repo.get_by_title(user.id, title)
        if not key:
            app_logger.info("API key not found", user_id=user.id, title=title)
            return None
        return await self.decrypt_key(key.key_encrypted)

    async def set_key(self, user_id: int, title: str, raw_key: str, is_active: bool = True) -> None:
        encrypted = self.fernet.encrypt(raw_key.encode()).decode()
        await self.repo.upsert_key(user_id, title, encrypted, is_active=is_active)

    async def disable_key(self, telegram_id: int):
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        await self.repo.deactivate_user_keys(user.id)

    async def validate_wb_api_key(self, key: str) -> bool:
        return len(key) > 30

    async def check_request_to_wb(self, key: str) -> bool:
        return True

    async def set_api_key_with_subscription_check(
        self,
        telegram_id: int,
        title: str,
        raw_key: str,
        subscription_service: SubscriptionService,
    ) -> tuple[bool, str]:
        """
        Сохраняет ключ API с учётом подписки.
        Возвращает:
        - is_active: bool — активен ли ключ.
        - status: str — один из: "active", "trial_activated", "inactive".
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("User not found")
        # Проверка на активную подписку
        if await subscription_service.has_active_subscription(user.id):
            await self.set_key(user.id, title, raw_key, is_active=True)
            return "active"

        # Можно ли дать пробную подписку?
        if await subscription_service.check_trial(user.id):
            await subscription_service.create_subscription(user.id, plan="trial")
            await self.set_key(user.id, title, raw_key, is_active=True)
            return "trial_activated"

        # Иначе сохраняем неактивный ключ
        await self.set_key(user.id, title, raw_key, is_active=False)
        return "inactive"
