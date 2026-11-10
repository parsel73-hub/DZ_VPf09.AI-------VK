"""Утилиты: логирование, текст, имитация набора, ошибки."""

from utils.errors import AIUnavailableError, BotError, StorageError, fallback_text
from utils.logger import setup_logging
from utils.text import normalize_user_text, truncate_vk
from utils.typing import (
    ThinkingPlaceholder,
    estimate_typing_delay,
    set_typing,
    typing_loop,
)

__all__ = [
    "AIUnavailableError",
    "BotError",
    "StorageError",
    "ThinkingPlaceholder",
    "estimate_typing_delay",
    "fallback_text",
    "normalize_user_text",
    "set_typing",
    "setup_logging",
    "truncate_vk",
    "typing_loop",
]
