"""Настройки проекта из переменных окружения (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Централизованные настройки приложения.

    Все значения читаются из .env; критичные параметры проверяются
    при старте бота (см. ``validate``).
    """

    # ── ВКонтакте ─────────────────────────────────────────
    vk_group_token: str
    vk_group_id: int

    # ── Gemini через ProxyAPI ─────────────────────────────
    proxyapi_key: str
    gemini_model: str
    proxyapi_base_url: str
    google_api_version: str

    # ── Параметры генерации ───────────────────────────────
    temperature: float
    max_output_tokens: int

    # ── Память и хранилище ────────────────────────────────
    max_history: int
    users_dir: str

    # ── Лимиты сообщений VK ───────────────────────────────
    max_message_length: int

    # ── Имитация набора текста ────────────────────────────
    typing_enabled: bool
    typing_speed_chars_per_sec: int
    typing_max_seconds: float

    # ── Прочее ────────────────────────────────────────────
    request_timeout_sec: float
    request_retries: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Загрузка настроек из переменных окружения с дефолтами."""
        return cls(
            vk_group_token=os.getenv("VK_GROUP_TOKEN", ""),
            vk_group_id=int(os.getenv("VK_GROUP_ID", "0")),
            proxyapi_key=os.getenv("PROXYAPI_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            proxyapi_base_url=os.getenv(
                "PROXYAPI_BASE_URL", "https://api.proxyapi.ru"
            ),
            google_api_version=os.getenv("GOOGLE_API_VERSION", "v1beta"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            max_output_tokens=int(
                os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")
            ),
            max_history=int(os.getenv("MAX_HISTORY", "100")),
            users_dir=os.getenv("USERS_DIR", "users"),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "4096")),
            typing_enabled=os.getenv(
                "TYPING_ENABLED", "true"
            ).lower() in ("1", "true", "yes", "on"),
            typing_speed_chars_per_sec=int(
                os.getenv("TYPING_SPEED", "40")
            ),
            typing_max_seconds=float(
                os.getenv("TYPING_MAX_SECONDS", "8")
            ),
            request_timeout_sec=float(
                os.getenv("REQUEST_TIMEOUT_SEC", "60")
            ),
            request_retries=int(os.getenv("REQUEST_RETRIES", "2")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> None:
        """Проверка обязательных значений при старте."""
        missing = [
            name
            for name, value in (
                ("VK_GROUP_TOKEN", self.vk_group_token),
                ("PROXYAPI_KEY", self.proxyapi_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Не заданы обязательные переменные окружения: "
                + ", ".join(missing)
                + ". Скопируйте .env.example в .env и заполните ключи."
            )
