"""Кастомные исключения и fallback-тексты."""

from __future__ import annotations


class BotError(Exception):
    """Базовое исключение приложения."""


class AIUnavailableError(BotError):
    """AI-сервис недоступен после всех попыток — нужен fallback."""


class StorageError(BotError):
    """Ошибка JSON-хранилища."""


def fallback_text() -> str:
    """Дружелюбное сообщение при недоступности Gemini."""
    return (
        "⚠️ К сожалению, AI-модель сейчас недоступна — "
        "проблемы сети или лимиты на стороне провайдера.\n\n"
        "Попробуйте повторить запрос через минуту. "
        "Ваша переписка сохранена и не потеряна."
    )
