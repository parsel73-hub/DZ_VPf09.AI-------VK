"""Модели данных: пользователь, диалоги, сообщения, режимы."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CommunicationMode(str, Enum):
    """Режимы общения (системные промпты)."""

    ASSISTANT = "assistant"
    PROGRAMMER = "programmer"
    TEACHER = "teacher"
    BUSINESS = "business"
    FRIEND = "friend"

    @property
    def title(self) -> str:
        """Человек-читаемое название режима."""
        return {
            self.ASSISTANT: "🤖 Обычный помощник",
            self.PROGRAMMER: "💻 Программист",
            self.TEACHER: "📚 Преподаватель",
            self.BUSINESS: "📊 Бизнес-консультант",
            self.FRIEND: "😊 Дружелюбный собеседник",
        }[self]

    @classmethod
    def from_str(cls, s: str) -> CommunicationMode:
        """Безопасный перевод строки в режим (с дефолтом)."""
        try:
            return cls(s)
        except ValueError:
            return cls.ASSISTANT


# ── Сообщения ────────────────────────────────────────────────────────


@dataclass
class ChatMessage:
    """Одно сообщение в истории диалога."""

    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str  # ISO-8601

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(
                str(self.timestamp)
            ).isoformat()

    @property
    def ts(self) -> datetime:
        """Парсенная дата/время."""
        return datetime.fromisoformat(self.timestamp)

    @classmethod
    def user(cls, text: str) -> ChatMessage:
        """Создать сообщение пользователя с текущим timestamp."""
        return cls(
            role="user",
            content=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def assistant(cls, text: str) -> ChatMessage:
        """Создать сообщение ассистента с текущим timestamp."""
        return cls(
            role="assistant",
            content=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def system(cls, text: str) -> ChatMessage:
        """Создать системное сообщение (service layer)."""
        return cls(
            role="system",
            content=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatMessage:
        return cls(
            role=str(data.get("role", "user")),
            content=str(data.get("content", "")),
            timestamp=str(data.get("timestamp", "")),
        )


# ── Диалоги ──────────────────────────────────────────────────────────


@dataclass
class Dialog:
    """Один диалог пользователя."""

    id: str
    title: str
    mode: str  # key из COMMUNICATION_MODES
    messages: list[ChatMessage] = field(default_factory=list)

    def add_message(self, msg: ChatMessage) -> None:
        """Добавить сообщение в историю."""
        self.messages.append(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "mode": self.mode,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dialog:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            mode=str(data.get("mode", "assistant")),
            messages=[
                ChatMessage.from_dict(m)
                for m in data.get("messages", [])
            ],
        )


# ── Состояние пользователя ───────────────────────────────────────────


@dataclass
class UserState:
    """Полное состояние пользователя (один JSON-файл)."""

    user_id: int
    dialogs: dict[str, Dialog] = field(default_factory=dict)
    active_dialog_id: str = ""
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def active_dialog(self) -> Dialog | None:
        """Возвращает активный диалог или None."""
        return self.dialogs.get(self.active_dialog_id)

    def set_active(self, dialog_id: str) -> None:
        """Делает диалог активным."""
        self.active_dialog_id = dialog_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "dialogs": {
                k: v.to_dict() for k, v in self.dialogs.items()
            },
            "active_dialog_id": self.active_dialog_id,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserState:
        dialogs = {
            k: Dialog.from_dict(v)
            for k, v in data.get("dialogs", {}).items()
        }
        return cls(
            user_id=int(data["user_id"]),
            dialogs=dialogs,
            active_dialog_id=str(data.get("active_dialog_id", "")),
            settings=data.get("settings", {}),
        )
