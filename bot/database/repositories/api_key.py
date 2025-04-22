from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WbApiKey
from .base import SQLAlchemyRepository


class WbApiKeyRepository(SQLAlchemyRepository[WbApiKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WbApiKey)

    async def get_active(self, user_id: int) -> list[WbApiKey]:
        stmt = select(WbApiKey).where(
            WbApiKey.user_id == user_id,
            WbApiKey.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_title(self, user_id: int, title: str) -> WbApiKey | None:
        stmt = select(WbApiKey).where(
            WbApiKey.user_id == user_id,
            WbApiKey.title == title
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
