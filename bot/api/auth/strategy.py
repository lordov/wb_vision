import base64
from abc import ABC, abstractmethod


class AuthStrategy(ABC):
    @abstractmethod
    def get_headers(self) -> dict:
        """
        Возвращает заголовки авторизации.
        """
        pass


class BasicAuthStrategy(AuthStrategy):
    def __init__(self, username: str, password: str):
        if not username or not password:
            raise ValueError(
                "Username and password are required for BasicAuthStrategy.")
        self.username = username
        self.password = password

    def get_headers(self) -> dict:
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept-Encoding": "gzip"
        }


class APIKeyAuthStrategy(AuthStrategy):
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for APIKeyAuthStrategy.")
        self.api_key = api_key

    def get_headers(self) -> dict:
        return {"Authorization": self.api_key}
