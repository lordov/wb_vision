import asyncio
import aiohttp


# Список порогов из JS-функции volHostV2
BASKET_THRESHOLDS = [
    143, 287, 431, 719, 1007, 1061, 1115, 1169, 1313, 1601,
    1655, 1919, 2045, 2189, 2405, 2621, 2837, 3053, 3269,
    3485, 3701, 3917, 4133, 4349, 4565
]


def get_estimated_basket(nm_id: int) -> str:
    s = nm_id // 100000
    for i, max_val in enumerate(BASKET_THRESHOLDS, start=1):
        if s <= max_val:
            return f"{i:02}"
    return "26"


def build_url(nm_id: int, basket: str) -> str:
    short_id = nm_id // 100000
    return f"https://basket-{basket}.wbbasket.ru/vol{short_id}/part{nm_id // 1000}/{nm_id}/images/big/1.webp"


async def get_working_photo_url(nm_id: int, session: aiohttp.ClientSession) -> str:
    estimated = int(get_estimated_basket(nm_id))
    
    for basket in range(estimated, 31):  # Проверяем с "предположенного" до 30
        url = build_url(nm_id, f"{basket:02}")
        async with session.head(url) as resp:
            if resp.status == 200:
                return url
    return ""  # Не нашли рабочий вариант


async def main():
    nm_id = 240451299
    async with aiohttp.ClientSession() as session:
        photo_url = await get_working_photo_url(nm_id, session)
        print("📷", photo_url or "Не удалось найти ссылку")


if __name__ == "__main__":
    asyncio.run(main())
