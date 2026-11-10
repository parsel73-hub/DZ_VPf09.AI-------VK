"""Основной файл бота — точка входа и конфигурация.

Запуск:
    python bot.py

Бот использует VK Long Poll (асинхронный режим).
Для работы нужен .env (скопируйте .env.example).
"""

from __future__ import annotations

import asyncio
import logging
import sys

from vkbottle import Bot

from config.prompts import COMMUNICATION_MODES
from config.settings import Settings
from handlers.message_handlers import register_handlers
from services.ai_service import AIService
from services.dialog_manager import DialogManager
from services.memory_manager import MemoryManager
from storage.json_storage import JsonUserStorage
from utils.errors import BotError
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Сборка приложения и запуск Long Poll."""
    # ── Настройки ──────────────────────────────────────────────────
    settings = Settings.from_env()
    settings.validate()
    setup_logging(settings.log_level)
    logger.info(
        "Запуск бота | модель=%s | история=%d | typing=%s",
        settings.gemini_model,
        settings.max_history,
        settings.typing_enabled,
    )

    # ── Компоненты ─────────────────────────────────────────────────
    storage = JsonUserStorage(settings.users_dir)
    await storage.ensure_dir()

    dialog_manager = DialogManager(storage)
    memory_manager = MemoryManager(dialog_manager, settings.max_history)

    ai_service = AIService(
        api_key=settings.proxyapi_key,
        model=settings.gemini_model,
        base_url=settings.proxyapi_base_url,
        api_version=settings.google_api_version,
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens,
        timeout_sec=settings.request_timeout_sec,
        retries=settings.request_retries,
    )

    logger.info(
        "Системные промпты (%d режимов): %s",
        len(COMMUNICATION_MODES),
        ", ".join(COMMUNICATION_MODES),
    )

    # ── VK-бот ─────────────────────────────────────────────────────
    bot = Bot(token=settings.vk_group_token)

    register_handlers(
        bot,
        dialog_manager,
        memory_manager,
        ai_service,
        max_message_length=settings.max_message_length,
        typing_enabled=settings.typing_enabled,
        typing_speed=settings.typing_speed_chars_per_sec,
        typing_max_seconds=settings.typing_max_seconds,
    )

    # ── Запуск ─────────────────────────────────────────────────────
    logger.info("Long Poll запущен. Ctrl+C для остановки.")
    await bot.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
    except BotError as e:
        logger.critical("Критическая ошибка: %s", e)
        sys.exit(1)
    except RuntimeError as e:
        logger.critical("Ошибка конфигурации: %s", e)
        sys.exit(1)
