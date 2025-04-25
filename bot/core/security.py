from cryptography.fernet import Fernet
from bot.core.config import settings


fernet = Fernet(settings.fernet_secret.get_secret_value())


def encrypt_api_key(api_key: str) -> str:
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
