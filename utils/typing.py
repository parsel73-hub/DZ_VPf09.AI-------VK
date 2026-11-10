"""Имитация набора текста и статус «бот думает…».

Механика:
  1. ``set_typing`` включает индикатор «печатает…» (messages.setActivity).
  2. ``ThinkingPlaceholder`` отправляет служебное сообщение
     «⏳ Бот думает…», которое потом редактируется на готовый ответ
     (messages.edit) — пользователь не видит двух сообщений подряд.
  3. ``estimate_typing_delay`` считает паузу «как живой человек»:
     длина ответа / скорость набора, но не больше лимита.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from vkbottle import API

logger = logging.getLogger(__name__)


async def set_typing(api: API, peer_id: int) -> None:
    """Включает статус «печатает…» для собеседника."""
    try:
        await api.messages.set_activity(peer_id=peer_id, type="typing")
    except Exception as e:  # noqa: BLE001
        logger.debug("set_typing failed: %s", e)


async def typing_loop(
    api: API,
    peer_id: int,
    stop: asyncio.Event,
    interval_sec: int = 8,
) -> None:
    """Держит статус «печатает…», пока не придёт ответ.

    Статус VK живёт ~10-15 секунд, поэтому цикл обновляет его
    каждые ``interval_sec`` до сигнала ``stop``.
    """
    while not stop.is_set():
        await set_typing(api, peer_id)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_sec)
        except asyncio.TimeoutError:
            continue


def estimate_typing_delay(
    text: str,
    speed_chars_per_sec: int,
    max_seconds: float,
) -> float:
    """Сколько секунд «печатать» ответ (защита от мгновенных простыней)."""
    if speed_chars_per_sec <= 0:
        return 0.0
    return min(len(text) / speed_chars_per_sec, max_seconds)


class ThinkingPlaceholder:
    """Служебное сообщение «бот думает…», редактируемое на ответ."""

    THINKING_TEXT = "⏳ Бот думает…"

    def __init__(self, api: API, peer_id: int) -> None:
        self._api = api
        self._peer_id = peer_id
        self._message_id: int | None = None

    async def start(self) -> None:
        """Отправляет заглушку и запоминает id сообщения."""
        try:
            response = await self._api.messages.send(
                peer_id=self._peer_id,
                message=self.THINKING_TEXT,
                random_id=_random_id(),
            )
            self._message_id = _extract_message_id(response)
        except Exception as e:  # noqa: BLE001
            logger.debug("Placeholder send failed: %s", e)

    async def finalize(self, text: str, keyboard: str | None = None) -> None:
        """Редактирует заглушку в готовый ответ.

        Если редактирование недоступно — удаляет заглушку и отправляет
        обычное сообщение.
        """
        if self._message_id is not None:
            try:
                await self._api.messages.edit(
                    peer_id=self._peer_id,
                    message_id=self._message_id,
                    message=text,
                    keyboard=keyboard,
                )
                return
            except Exception as e:  # noqa: BLE001
                logger.debug(
                    "messages.edit failed (%s), fallback to send", e
                )
                await self._delete_placeholder()
        await self._api.messages.send(
            peer_id=self._peer_id,
            message=text,
            keyboard=keyboard,
            random_id=_random_id(),
        )

    async def abort(self) -> None:
        """Убирает заглушку (например, при ошибке AI)."""
        if self._message_id is not None:
            await self._delete_placeholder()

    async def _delete_placeholder(self) -> None:
        try:
            await self._api.messages.delete(
                message_ids=[self._message_id],  # type: ignore[list-item]
                peer_id=self._peer_id,
                delete_for_all=False,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("Placeholder delete failed: %s", e)
        finally:
            self._message_id = None


def _random_id() -> int:
    """Уникальный random_id для messages.send (защита от дедупликации VK)."""
    import random

    return random.randint(1, 2**30)


def _extract_message_id(response: Any) -> int | None:
    """Достаёт id отправленного сообщения из ответа API.

    messages.send с peer_id возвращает int; с peer_ids — список объектов.
    """
    if isinstance(response, int):
        return response
    if isinstance(response, dict):
        return response.get("id") or response.get("message_id")
    if isinstance(response, list) and response:
        response = response[0]
    return getattr(response, "message_id", None) or getattr(
        response, "id", None
    )
