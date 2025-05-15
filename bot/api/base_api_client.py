import json
import time
import aiohttp
import asyncio
import inspect

from typing import Optional, Any
from cachetools import TTLCache
from collections import deque
from .auth.strategy import AuthStrategy
from ..core.logging import api_logger
from ..core.security import decrypt_api_key


class BaseAPIClient:
    """
    BaseAPIClient is a class for making HTTP requests with caching and error handling.

    Attributes:
        headers (dict): HTTP headers for the requests.
        cache (TTLCache): Cache for storing responses.
        logger_debug (logging.Logger): Logger for debug messages.
        logger_api_error (logging.Logger): Logger for API error messages.
        logger_success (logging.Logger): Logger for successful requests.
        logger_error (logging.Logger): Logger for general errors.
    """

    def __init__(
        self,
        # auth_strategy: AuthStrategy,
        token: str,
        cache_ttl: int = 3600
    ):
        # self.auth_strategy = auth_strategy
        self.token = token
        self.cache = TTLCache(maxsize=1000, ttl=cache_ttl)

        # Логгеры
        self.api_logger = api_logger

    def set_cache(self, cache: TTLCache) -> None:
        """
        Устанавливает новый кэш для клиента.

        :param cache: Новый объект кэша.
        """
        self.cache = cache

    async def _handle_error(
        self,
        api_error: aiohttp.ClientResponseError,
        response: aiohttp.ClientResponse,
        method: str,
        url: str,
        caller: str
    ) -> Optional[str]:
        """
        Обработка ошибок HTTP-запросов.

        :param e: Исключение aiohttp.ClientResponseError.
        :param response: Объект ответа aiohttp.ClientResponse.
        :param method: HTTP-метод.
        :param url: URL запроса.
        :param caller: Имя вызывающей функции.
        :return: 'RETRY' для повторных попыток или None для завершения.
        """
        try:
            # Попытка прочитать данные из response.read()
            error_content = await response.read()
            if error_content:
                try:
                    error_details = error_content.decode('utf-8')
                    error_details = json.loads(error_details)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    error_details = error_content.decode(
                        'utf-8', errors='ignore')
        except aiohttp.ClientConnectionError:
            # Если соединение закрыто, пробуем получить данные из буфера StreamReader
            if hasattr(response.content, '_buffer') and isinstance(response.content._buffer, deque):
                raw_data = b''.join(response.content._buffer)
                if raw_data:
                    try:
                        error_details = raw_data.decode('utf-8')
                        error_details = json.loads(error_details)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        error_details = raw_data.decode(
                            'utf-8', errors='ignore')
                else:
                    error_details = "No data available in buffer."
            else:
                error_details = "Connection closed without data."

        # Логирование ошибок
        if api_error.status == 401:
            self.api_logger.error(
                f"Unauthorized (401): {method} {url} ({caller}), Details: {error_details}")
            return None

        elif api_error.status in {400, 404}:
            self.api_logger.error(
                f"Bad Request {api_error.status}: {method} {url} ({caller}), Details: {error_details}")
            return None

        elif api_error.status == 429:
            self.api_logger.warning(
                f"Retryable error {api_error.status} {method} {url} ({caller})")
            return "RETRY"

        elif api_error.status in {500, 502, 503, 504}:
            self.api_logger.error(
                f"Server error {api_error.status} {method} {url} ({caller}), Message: {api_error.message}")
            return "RETRY"

        else:
            self.api_logger.error(
                f"HTTP Error {api_error.status} {caller}: {method} {url}, Reason: {api_error.message}")
            return None

    async def _request(
            self,
            method: str,
            url: str,
            params: Optional[dict[str, Any]] = None,
            json: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            max_retries: int = 5
    ) -> Optional[dict[str, Any]]:
        """
        Базовый метод для выполнения запросов с логированием и обработкой ошибок.

        :param method: HTTP-метод (GET, POST и т.д.).
        :param url: Полный URL запроса.
        :param params: Параметры запроса (для GET).
        :param json: Тело запроса (для POST/PUT).
        :param max_retries: Количество повторных попыток.
        :param headers: Произвольные заголовки.
        :return: JSON-ответ сервера или None в случае ошибки.
        """
        retries = 0
        # Заголовки из стратегии
        auth_headers = {
            "Authorization": f"{decrypt_api_key(self.token)}"}
        caller = inspect.stack()[1].function
        while retries <= max_retries:
            async with aiohttp.ClientSession() as session:
                try:
                    start_time = time.time()
                    async with session.request(
                            method, url, params=params, json=json, headers=headers or auth_headers) as response:
                        duration = time.time() - start_time
                        response.raise_for_status()
                        if response.status == 200:
                            self.api_logger.info(
                                f"Response {response.status} ({caller}) Duration: {
                                    duration:.2f}s : {method} {url}"
                            )
                        # Проверяем Content-Type для выбора метода обработки
                        if response.content_type == 'application/json':
                            return await response.json()
                        elif response.content_type == 'application/xml':
                            return await response.text()
                        else:
                            self.api_logger.error(
                                f"Неподдерживаемый формат ответа: {response.content_type}")
                            return None
                except aiohttp.ClientResponseError as error:
                    result = await self._handle_error(error, response, method, url, caller)
                    if result == "RETRY":
                        retries += 1
                        await asyncio.sleep(30 * retries)
                        continue
                    return result
                except aiohttp.ClientPayloadError as error:
                    self.api_logger.error(
                        f"Transfer error {url} (Caller: {caller}): {str(error)}")
                    retries += 1
                    await asyncio.sleep(3 * retries)
                    continue
                except Exception as error:
                    self.api_logger.error(
                        f"Unexpected error {url} (Caller: {caller}) {response.status}: {
                            str(error)}"
                    )
                    return None
        self.api_logger.error(
            f"Failed after retries: {method} {url} (Caller: {caller})")
        return None

    async def _download(self, file_url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                if resp.status != 200:
                    return None
                return await resp.read()
