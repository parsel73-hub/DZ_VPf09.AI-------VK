"""Ограничение длины сообщений и защита от пустого ввода."""

from __future__ import annotations

VK_MESSAGE_LIMIT = 4096


def truncate_vk(text: str, limit: int = VK_MESSAGE_LIMIT) -> str:
    """Обрезает текст под лимит сообщения VK.

    Если текст длиннее лимита, обрезается по границе слова,
    и добавляется многоточие.
    """
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    # Пытаемся обрезать по последнему пробелу, чтобы не рвать слово
    space_idx = cut.rfind(" ")
    if space_idx > limit // 2:
        cut = cut[:space_idx]
    return cut.rstrip() + "…"


def normalize_user_text(raw: str | None) -> str | None:
    """Возвращает очищенный текст сообщения или None, если ввод пуст.

    Защита от пустых сообщений: пробелы, переводы строк, None.
    """
    if not raw:
        return None
    cleaned = raw.strip()
    return cleaned or None
