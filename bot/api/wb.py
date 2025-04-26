from typing import Optional
from .base_api_client import BaseAPIClient


class WBAPIClient(BaseAPIClient):
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
        # Получение последней даты из базы данных
        # date_from_db = await db_manager.get_last_date(table_name='wb_sales', date_column='date')
        if date_from_db is None:
            date_from_db = date_from

        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/sales?dateFrom={
            date_from_db}"
        return await self._request("GET", url)

    # Заказы
    async def get_orders(
            self,
            date_from: str = '2025-03-20'
    ) -> Optional[dict]:
        """
        Получение данных о заказах начиная с указанной даты.

        :param date_from: Дата начала периода в формате YYYY-MM-DD.
        :param db_manager: Объект DatabaseManager для взаимодействия с базой данных.
        :return: JSON с данными о заказах или None в случае ошибки.
        """
        date_from_db = None
        # date_from_db = await db_manager.get_last_date(table_name='wb_orders', date_column='date')
        if date_from_db is None:
            date_from_db = date_from
        url = f"https://statistics-api.wildberries.ru/api/v1/supplier/orders?dateFrom={
            date_from}"
        return await self._request("GET", url)
    
    async def ping_wb(self):
        url = "https://statistics-api.wildberries.ru/ping"
        response = await self._request("GET", url)
        return response


if __name__ == "__main__":
    print(f'{__name__} Started on its own')
else:
    print(f'{__name__} imported')
