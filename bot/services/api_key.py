from cryptography.fernet import Fernet, InvalidToken

from bot.database.repositories.api_key import WbApiKeyRepository
from bot.database.models import ApiKey
from ..core.logging import app_logger


class ApiKeyDecryptionError(Exception):
    pass


class ApiKeyService:
    def __init__(self, repo: WbApiKeyRepository, fernet: Fernet):
        self.repo = repo
        self.fernet = fernet

    async def get_user_key_titles(self, user_id: int) -> list[dict]:
        app_logger.info("Fetching API key titles", user_id=user_id)
        keys = await self.repo.get_active(user_id)
        return [{"id": key.id, "title": key.title} for key in keys]

    async def add_encrypt_key(self, user_id: int, raw_key: str, title: str = "API Key") -> ApiKey:
        app_logger.info("Encrypting and adding API key",
                        user_id=user_id, title=title)
        encrypted = self.fernet.encrypt(raw_key.encode()).decode()
        key = await self.repo.add_one({
            "user_id": user_id,
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

    async def get_decrypted_by_title(self, user_id: int, title: str) -> str | None:
        app_logger.info("Getting and decrypting API key by title",
                        user_id=user_id, title=title)
        key = await self.repo.get_by_title(user_id, title)
        if not key:
            app_logger.info("API key not found", user_id=user_id, title=title)
            return None
        return await self.decrypt_key(key.key_encrypted)

    async def set_key(self, user_id: int, title: str, raw_key: str):
        await self.repo.deactivate_user_keys(user_id)
        await self.add_encrypt_key(user_id, title, raw_key)
    
    async def disable_key(self, user_id: int, title: str):
        await self.repo.deactivate_user_keys(user_id)
