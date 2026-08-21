from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.i18n import LANGUAGE_NAMES, t

USER_SELECTABLE_LANGUAGES = ("ru", "en")


def language_keyboard(context: str = "start") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LANGUAGE_NAMES[language],
                    callback_data=f"language:{context}:{language}",
                )
                for language in USER_SELECTABLE_LANGUAGES
            ]
        ]
    )


def start_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("button.link", language))],
            [KeyboardButton(text=t("button.register", language))],
        ],
        resize_keyboard=True,
    )


def main_menu_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("button.parcels", language)),
                KeyboardButton(text=t("button.track", language)),
            ],
            [
                KeyboardButton(text=t("button.contacts", language)),
                KeyboardButton(text=t("button.schedule", language)),
            ],
            [
                KeyboardButton(text=t("button.china_address", language)),
                KeyboardButton(text=t("button.profile", language)),
            ],
            [
                KeyboardButton(text=t("button.delivered", language)),
                KeyboardButton(text=t("button.help", language)),
            ],
            [KeyboardButton(text=t("button.language", language))],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("button.cancel", language))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
