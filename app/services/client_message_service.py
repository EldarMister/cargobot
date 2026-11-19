import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from app.db.models import User

logger = logging.getLogger(__name__)


class ClientMessageError(Exception):
    def __init__(self, detail: str, status_code: int = 409):
        super().__init__(detail)
        self.status_code = status_code


def client_message_unavailable_reason(user: User) -> str | None:
    if not user.telegram_id:
        return "Telegram клиента не привязан. Клиент должен открыть бота и привязать свой H-код."
    if not user.has_access():
        return "Клиент заблокирован в системе. Сначала снимите блокировку."
    return None


async def send_client_message(
    bot: Bot, user: User, text: str, *, expected_telegram_id: int, admin_id: int
) -> int:
    reason = client_message_unavailable_reason(user)
    if reason:
        raise ClientMessageError(reason)
    if user.telegram_id != expected_telegram_id:
        raise ClientMessageError("Telegram клиента изменился. Откройте карточку заново.")
    text = text.strip()
    if not text or len(text.encode("utf-16-le")) // 2 > 4096:
        raise ClientMessageError("Введите сообщение длиной от 1 до 4096 символов.", 422)
    try:
        # Admin text is plain text, even when the bot's default parse mode is HTML.
        message = await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode=None)
    except TelegramForbiddenError as exc:
        raise ClientMessageError("Клиент заблокировал бота или запретил сообщения.") from exc
    except TelegramBadRequest as exc:
        raise ClientMessageError(
            "Telegram-чат клиента недоступен. Попросите клиента снова запустить бота."
        ) from exc
    except TelegramRetryAfter as exc:
        raise ClientMessageError("Telegram временно ограничил отправку. Попробуйте позже.", 429) from exc
    except TelegramAPIError as exc:
        logger.warning("Client message not confirmed: client_id=%s error=%s", user.id, type(exc).__name__)
        raise ClientMessageError(
            "Не удалось подтвердить отправку. Перед повтором уточните, получил ли клиент сообщение.",
            502,
        ) from exc
    logger.info(
        "Admin message sent: admin_id=%s client_id=%s message_id=%s",
        admin_id, user.id, message.message_id,
    )
    return message.message_id
