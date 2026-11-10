"""Менеджер памяти: история сообщений, обрезка до лимита, контекст.

Хранит максимум ``max_history`` последних сообщений в диалоге;
старые сообщения автоматически удаляются.
"""

from __future__ import annotations

import logging

from models.entities import ChatMessage, Dialog
from services.dialog_manager import DialogManager

logger = logging.getLogger(__name__)


class MemoryManager:
    """Управление историей сообщений активного диалога."""

    def __init__(self, dialog_manager: DialogManager, max_history: int) -> None:
        self._dialogs = dialog_manager
        self._max_history = max_history

    def add_user_message(self, dialog: Dialog, text: str) -> ChatMessage:
        """Добавляет сообщение пользователя в историю."""
        msg = ChatMessage.user(text)
        dialog.add_message(msg)
        self._trim(dialog)
        return msg

    def add_assistant_message(self, dialog: Dialog, text: str) -> ChatMessage:
        """Добавляет ответ ассистента в историю."""
        msg = ChatMessage.assistant(text)
        dialog.add_message(msg)
        self._trim(dialog)
        return msg

    def build_context(self, dialog: Dialog) -> list[ChatMessage]:
        """Возвращает окно контекста для запроса к модели.

        Берутся последние ``max_history`` сообщений; system prompt
        добавляется на уровне AIService (через GenerateContentConfig),
        поэтому здесь — только user/assistant история.
        """
        return dialog.messages[-self._max_history:]

    def clear_history(self, dialog: Dialog) -> None:
        """Полностью очищает историю диалога."""
        dialog.messages.clear()

    def message_count(self, dialog: Dialog) -> int:
        return len(dialog.messages)

    def _trim(self, dialog: Dialog) -> None:
        """Автоматическая обрезка старых сообщений."""
        if len(dialog.messages) > self._max_history:
            dialog.messages = dialog.messages[-self._max_history:]
