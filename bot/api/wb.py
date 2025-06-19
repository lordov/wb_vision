from typing import Optional

from bot.api.auth.strategy import APIKeyAuthStrategy
from bot.core.security import decrypt_api_key
from bot.schemas.wb import OrderWBCreate, StockWBCreate
from .base_api_client import BaseAPIClient


class WBAPIClient(BaseAPIClient):
    def __init__(self, token: Optional[str] = None, cache_ttl: int = 3600, plain_token: Optional[str] = None):
        self.plain_token = plain_token
        if token:
            # Создаем APIKeyAuthStrategy с расшифрованным токеном
            decrypted_token = decrypt_api_key(token)
            auth_strategy = APIKeyAuthStrategy(decrypted_token)
        elif plain_token:
            # Используем незашифрованный токен для проверки
            auth_strategy = APIKeyAuthStrategy(plain_token)
        else:
            auth_strategy = None

        # Вызываем конструктор базового класса с нашей стратегией
        super().__init__(auth_strategy=auth_strategy, cache_ttl=cache_ttl)

    # Продажи
    async def get_sales(
            self,
            date_from: Optional[str] = '2025-01-01'
    ) -> Optional[dict]:
        """
        Получение данных о продажах начиная с указанной даты.

        Если дата не указана, берется последняя доступная дата из базы данных.

        :param db_manager: Объект DatabaseManager для взаимодействия с базой данных.
        :param date_from: Дата начала периода в формате YYYY-MM-DD (опционально).
        :return: JSON с данными о продажах или None в случае ошибки.
        """

        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/sales?dateFrom={
            date_from}"
        return await self._request("GET", url)

    # Заказы
    async def get_orders(
            self,
            user_id: int,
            date_from: str = '2025-05-19'
    ) -> list[OrderWBCreate]:
        """
        Получение данных о заказах начиная с указанной даты.

        :param date_from: Дата начала периода в формате YYYY-MM-DD.
        :param db_manager: Объект DatabaseManager для взаимодействия с базой данных.
        :return: list[OrderWBCreate] с данными о заказах или None в случае ошибки.
        """
        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/orders?dateFrom={
            date_from}"
        orders_data = await self._request("GET", url)
        return [OrderWBCreate(**order, user_id=user_id) for order in orders_data]

    async def ping_wb(self):
        url = "https://statistics-api.wildberries.ru/ping"
        response = await self._request("GET", url)
        return response

    async def get_stocks(self, user_id: int, date_from: str = '2025-05-19'):
        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/stocks?dateFrom={
            date_from}"
        stocks_data = await self._request("GET", url)
        return [StockWBCreate(**stock, user_id=user_id) for stock in stocks_data]


if __name__ == "__main__":
    print(f'{__name__} Started on its own')
else:
    print(f'{__name__} imported')
