from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from fluentogram import TranslatorHub


class TranslatorRunnerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:

        user: User = data.get('event_from_user')

        if user is None:
            return await handler(event, data)

        hub: TranslatorHub = data.get('_translator_hub')
        data['i18n'] = hub.get_translator_by_locale(locale=user.language_code)

        return await handler(event, data)
