"""Генерация VK-клавиатур.

Клавиатуры строятся на каждом вызове (payload содержит актуальные id),
поэтому функции — чистые: диалоги на вход, JSON-строка на выход.
"""

from __future__ import annotations

from vkbottle import Keyboard, KeyboardButtonColor, Text

from config.prompts import COMMUNICATION_MODES
from models.entities import Dialog, UserState

# ── Главное меню ─────────────────────────────────────────────────────


def main_menu_kb() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("🆕 Новый диалог", payload={"cmd": "new_dialog"}))
    kb.add(Text("📚 Диалоги", payload={"cmd": "show_dialogs"}))
    kb.row()
    kb.add(Text("🎭 Сменить режим", payload={"cmd": "show_modes"}))
    kb.add(Text("⚙️ Настройки", payload={"cmd": "show_settings"}))
    kb.row()
    kb.add(Text("❓ Помощь", payload={"cmd": "show_help"}))
    return kb.get_json()


# ── Список диалогов ──────────────────────────────────────────────────


def dialogs_list_kb(state: UserState) -> str:
    """Список диалогов: кнопка переключения + кнопка удаления на строку."""
    kb = Keyboard(one_time=False)
    for dialog in state.dialogs.values():
        marker = "✅ " if dialog.id == state.active_dialog_id else "💬 "
        kb.add(
            Text(
                f"{marker}{dialog.title}",
                payload={"cmd": "switch_dialog", "dialog_id": dialog.id},
            )
        )
        kb.add(
            Text(
                "🗑",
                payload={"cmd": "ask_delete_dialog", "dialog_id": dialog.id},
            ),
            color=KeyboardButtonColor.NEGATIVE,
        )
        kb.row()
    kb.add(Text("➕ Новый диалог", payload={"cmd": "new_dialog"}))
    kb.add(Text("◀️ Назад", payload={"cmd": "show_main_menu"}))
    return kb.get_json()


# ── Подтверждение удаления ───────────────────────────────────────────


def confirm_delete_kb(dialog_id: str) -> str:
    kb = Keyboard(one_time=True)
    kb.add(
        Text(
            "✅ Да, удалить",
            payload={"cmd": "confirm_delete_dialog", "dialog_id": dialog_id},
        ),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.add(Text("✖️ Отмена", payload={"cmd": "show_dialogs"}))
    return kb.get_json()


# ── Режимы общения ───────────────────────────────────────────────────


def modes_kb(active_mode: str) -> str:
    """Кнопки режимов; активный режим помечен галочкой."""
    kb = Keyboard(one_time=False)
    for key, info in COMMUNICATION_MODES.items():
        marker = "✅ " if key == active_mode else ""
        kb.add(
            Text(
                f"{info['emoji']} {info['title']}",
                payload={"cmd": "set_mode", "mode": key},
            )
        )
        kb.row()
    kb.add(Text("◀️ Назад", payload={"cmd": "show_main_menu"}))
    return kb.get_json()


# ── Настройки ────────────────────────────────────────────────────────


def settings_kb() -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text("🎭 Режим общения", payload={"cmd": "show_modes"}))
    kb.row()
    kb.add(Text("🤖 Текущая модель", payload={"cmd": "show_model_info"}))
    kb.row()
    kb.add(
        Text(
            "🧹 Очистить историю",
            payload={"cmd": "ask_clear_history"},
        ),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.row()
    kb.add(Text("◀️ Назад", payload={"cmd": "show_main_menu"}))
    return kb.get_json()


def confirm_clear_history_kb() -> str:
    kb = Keyboard(one_time=True)
    kb.add(
        Text(
            "✅ Да, очистить",
            payload={"cmd": "confirm_clear_history"},
        ),
        color=KeyboardButtonColor.NEGATIVE,
    )
    kb.add(Text("✖️ Отмена", payload={"cmd": "show_settings"}))
    return kb.get_json()


# ── Общие ────────────────────────────────────────────────────────────


def back_kb(target_cmd: str = "show_main_menu", label: str = "◀️ В меню") -> str:
    kb = Keyboard(one_time=False)
    kb.add(Text(label, payload={"cmd": target_cmd}))
    return kb.get_json()
