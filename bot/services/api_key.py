from cryptography.fernet import Fernet, InvalidToken

from bot.database.repositories.api_key import WbApiKeyRepository
from bot.database.models import WbApiKey


class WbApiKeyService:
    def __init__(self, repo: WbApiKeyRepository, fernet: Fernet):
        self.repo = repo
        self.fernet = fernet

    async def list_user_keys(self, user_id: int) -> list[dict]:
        keys = await self.repo.get_active(user_id)
        return [{"id": key.id, "title": key.title} for key in keys]

    async def add_key(self, user_id: int, title: str, raw_key: str) -> WbApiKey:
        encrypted = self.fernet.encrypt(raw_key.encode()).decode()
        return await self.repo.add_one({
            "user_id": user_id,
            "title": title,
            "key_encrypted": encrypted,
        })

    async def decrypt_key(self, encrypted_key: str) -> str:
        try:
            return self.fernet.decrypt(encrypted_key.encode()).decode()
        except InvalidToken:
            raise ValueError("Invalid key or corrupted data")

    async def get_decrypted_by_title(self, user_id: int, title: str) -> str | None:
        key = await self.repo.get_by_title(user_id, title)
        if not key:
            return None
        return await self.decrypt_key(key.key_encrypted)
