"""AIService — централизованный модуль работы с Gemini через ProxyAPI.

Использует google-genai SDK, направляя базовый адрес на ProxyAPI.
Поддерживает:
  - system prompt (через config.system_instruction)
  - передачу истории сообщений
  - повторные попытки при сетевых ошибках
  - fallback при недоступности API
"""

from __future__ import annotations

import asyncio
import logging

from google.genai import Client
from google.genai import errors as genai_errors
from google.genai.types import (
    Content,
    GenerateContentConfig,
    HttpOptions,
    Part,
)

from config.prompts import COMMUNICATION_MODES
from models.entities import ChatMessage, CommunicationMode
from utils.errors import AIUnavailableError

logger = logging.getLogger(__name__)


class AIService:
    """Асинхронный клиент Gemini через ProxyAPI.

    Модель и endpoint берутся из Settings, поэтому смена модели
    не требует правки кода — только .env.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        api_version: str,
        temperature: float,
        max_output_tokens: int,
        timeout_sec: float,
        retries: int,
    ) -> None:
        self._model = model
        self._retries = retries
        self._timeout = timeout_sec
        self._client = Client(
            api_key=api_key,
            http_options=HttpOptions(
                base_url=base_url,
                api_version=api_version,
                timeout=int(timeout_sec * 1000),
            ),
        )
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens

    @property
    def model_name(self) -> str:
        """Имя текущей модели для отображения в настройках."""
        return self._model

    # ── Публичный API ────────────────────────────────────────────────

    async def generate_reply(
        self,
        history: list[ChatMessage],
        mode: CommunicationMode,
    ) -> str:
        """Формирует контекст и запрашивает ответ у Gemini.

        Args:
            history: последние N сообщений диалога (user/assistant).
            mode: режим общения — определяет system prompt.

        Returns:
            Текст ответа модели.

        Raises:
            AIUnavailableError: если все попытки исчерпаны.
        """
        system_prompt = COMMUNICATION_MODES[mode.value]["system_prompt"]
        contents = self._build_contents(history)

        last_error: Exception | None = None
        for attempt in range(1, self._retries + 2):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=self._temperature,
                        max_output_tokens=self._max_output_tokens,
                    ),
                )
                text = self._extract_text(response)
                if text:
                    return text
                last_error = AIUnavailableError("Модель вернула пустой ответ")
            except genai_errors.APIError as e:
                # Ошибка API (4xx/5xx от провайдера)
                logger.warning(
                    "Gemini API error (attempt %d): %s", attempt, e
                )
                last_error = e
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                # Сетевые проблемы
                logger.warning(
                    "Network error (attempt %d): %s", attempt, e
                )
                last_error = e
            except Exception as e:  # noqa: BLE001
                logger.exception("Unexpected AI service error")
                last_error = e

            if attempt <= self._retries:
                await asyncio.sleep(1.5 * attempt)  # простой backoff

        raise AIUnavailableError(
            f"Gemini API недоступен после {self._retries + 1} попыток"
        ) from last_error

    # ── Внутренние методы ────────────────────────────────────────────

    @staticmethod
    def _build_contents(history: list[ChatMessage]) -> list[Content]:
        """Конвертирует историю в формат Gemini.

        Роль "assistant" маппится в "model" — так требует Google API.
        System prompt передаётся отдельно через config, поэтому
        сообщения с role="system" в contents не попадают.
        """
        contents: list[Content] = []
        for msg in history:
            if msg.role == "system" or not msg.content:
                continue
            role = "model" if msg.role == "assistant" else "user"
            contents.append(
                Content(role=role, parts=[Part(text=msg.content)])
            )
        return contents

    @staticmethod
    def _extract_text(response: object) -> str:
        """Извлекает текст из ответа, игнорируя «размышления» (thoughts)."""
        try:
            candidates = getattr(response, "candidates", None) or []
            parts_out: list[str] = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                for part in getattr(content, "parts", None) or []:
                    text = getattr(part, "text", None)
                    # У новых моделей reasoning-токены помечены как thought
                    if text and not getattr(part, "thought", False):
                        parts_out.append(text)
            return "".join(parts_out).strip()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to extract text from response")
            return ""
