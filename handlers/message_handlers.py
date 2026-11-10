"""VK-хендлеры: команды, кнопки и AI-чат.

Слой VK: принимает события, вызывает сервисы, форматирует ответы.
Логика AI здесь отсутствует — только оркестрация.
"""

from __future__ import annotations

import asyncio
import logging

from vkbottle import Bot
from vkbottle.bot import Message
from vkbottle.dispatch.rules import base

from config.prompts import COMMUNICATION_MODES
from keyboards.kb import (
    back_kb,
    confirm_clear_history_kb,
    confirm_delete_kb,
    dialogs_list_kb,
    main_menu_kb,
    modes_kb,
    settings_kb,
)
from models.entities import CommunicationMode
from services.ai_service import AIService
from services.dialog_manager import DialogManager
from services.memory_manager import MemoryManager
from utils.errors import AIUnavailableError, fallback_text
from utils.text import normalize_user_text, truncate_vk
from utils.typing import (
    ThinkingPlaceholder,
    estimate_typing_delay,
    typing_loop,
)

logger = logging.getLogger(__name__)


def register_handlers(
    bot: Bot,
    dialogs: DialogManager,
    memory: MemoryManager,
    ai: AIService,
    *,
    max_message_length: int,
    typing_enabled: bool,
    typing_speed: int,
    typing_max_seconds: float,
) -> None:
    """Регистрирует все обработчики на боте."""

    # ── Команды ──────────────────────────────────────────────────────

    @bot.on.message(base.CommandRule("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "👋 Привет! Я AI-ассистент.\n\n"
            "Просто напишите сообщение — я отвечу.\n"
            "Кнопки ниже помогут управлять диалогами и режимами.",
            keyboard=main_menu_kb(),
        )

    @bot.on.message(base.CommandRule("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(HELP_TEXT, keyboard=main_menu_kb())

    # ── Навигация по меню (payload-кнопки) ──────────────────────────

    @bot.on.message(base.PayloadMapRule({"cmd": "show_main_menu"}))
    async def show_menu(message: Message) -> None:
        await message.answer("Главное меню:", keyboard=main_menu_kb())

    @bot.on.message(base.PayloadMapRule({"cmd": "show_help"}))
    async def show_help(message: Message) -> None:
        await message.answer(HELP_TEXT, keyboard=main_menu_kb())

    @bot.on.message(base.PayloadMapRule({"cmd": "show_dialogs"}))
    async def show_dialogs(message: Message) -> None:
        state = await dialogs.get_state(message.from_id)
        await message.answer(
            f"📚 Ваши диалоги ({len(state.dialogs)}):",
            keyboard=dialogs_list_kb(state),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "show_settings"}))
    async def show_settings(message: Message) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = state.active_dialog
        mode = CommunicationMode.from_str(dialog.mode if dialog else "assistant")
        await message.answer(
            "⚙️ Настройки\n\n"
            f"🎭 Режим текущего диалога: {mode.title}\n"
            f"🤖 Модель: {ai.model_name}\n"
            f"💬 Сообщений в диалоге: {memory.message_count(dialog) if dialog else 0}",
            keyboard=settings_kb(),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "show_modes"}))
    async def show_modes(message: Message) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = state.active_dialog
        current = dialog.mode if dialog else "assistant"
        await message.answer(
            "🎭 Режимы общения\n\n"
            "Выберите режим — он применится к текущему диалогу:",
            keyboard=modes_kb(current),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "show_model_info"}))
    async def show_model_info(message: Message) -> None:
        await message.answer(
            f"🤖 Текущая модель: <b>{ai.model_name}</b>\n\n"
            "Модель подключена через ProxyAPI (Gemini API).\n"
            "Сменить модель можно в настройках окружения (.env).",
            keyboard=settings_kb(),
        )

    # ── Операции с диалогами ─────────────────────────────────────────

    @bot.on.message(base.PayloadMapRule({"cmd": "new_dialog"}))
    async def new_dialog(message: Message) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = dialogs.create_dialog(state)
        if dialog is None:
            await message.answer(
                "⚠️ Достигнут лимит диалогов. Удалите старые.",
                keyboard=back_kb("show_dialogs", "◀️ К диалогам"),
            )
            return
        await dialogs.save(state)
        await message.answer(
            f"🆕 Создан диалог «{dialog.title}».\n"
            "Напишите сообщение, чтобы начать общение.",
            keyboard=main_menu_kb(),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "switch_dialog"}))
    async def switch_dialog(message: Message, dialog_id: str) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = dialogs.switch_dialog(state, dialog_id)
        if dialog is None:
            await message.answer(
                "⚠️ Диалог не найден.", keyboard=back_kb("show_dialogs", "◀️ К диалогам")
            )
            return
        await dialogs.save(state)
        mode = CommunicationMode.from_str(dialog.mode)
        await message.answer(
            f"💬 Переключены на диалог «{dialog.title}» ({mode.title}).\n"
            "Контекст и режим теперь свои для этого диалога.",
            keyboard=main_menu_kb(),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "ask_delete_dialog"}))
    async def ask_delete_dialog(message: Message, dialog_id: str) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = state.dialogs.get(dialog_id)
        if dialog is None:
            await message.answer("⚠️ Диалог не найден.", keyboard=main_menu_kb())
            return
        if len(state.dialogs) <= 1:
            await message.answer(
                "🗑 Нельзя удалить последний диалог — вместо него очистите историю в настройках.",
                keyboard=back_kb("show_dialogs", "◀️ К диалогам"),
            )
            return
        await message.answer(
            f"Удалить диалог «{dialog.title}» со всей историей?",
            keyboard=confirm_delete_kb(dialog.id),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "confirm_delete_dialog"}))
    async def confirm_delete_dialog(message: Message, dialog_id: str) -> None:
        state = await dialogs.get_state(message.from_id)
        title = state.dialogs.get(dialog_id)
        name = title.title if title else "?"
        if dialogs.delete_dialog(state, dialog_id):
            await dialogs.save(state)
            await message.answer(
                f"🗑 Диалог «{name}» удалён.",
                keyboard=dialogs_list_kb(state),
            )
        else:
            await message.answer("⚠️ Не удалось удалить диалог.", keyboard=main_menu_kb())

    # ── Режимы ───────────────────────────────────────────────────────

    @bot.on.message(base.PayloadMapRule({"cmd": "set_mode"}))
    async def set_mode(message: Message, mode: str) -> None:
        state = await dialogs.get_state(message.from_id)
        mode_enum = CommunicationMode.from_str(mode)
        dialog = dialogs.set_mode(state, mode_enum)
        if dialog is None:
            await message.answer("⚠️ Нет активного диалога.", keyboard=main_menu_kb())
            return
        await dialogs.save(state)
        await message.answer(
            f"🎭 Режим «{mode_enum.title}» применён к диалогу «{dialog.title}».\n"
            "Стиль ответов изменится со следующего сообщения.",
            keyboard=main_menu_kb(),
        )

    # ── Очистка истории ──────────────────────────────────────────────

    @bot.on.message(base.PayloadMapRule({"cmd": "ask_clear_history"}))
    async def ask_clear_history(message: Message) -> None:
        await message.answer(
            "Очистить историю текущего диалога?",
            keyboard=confirm_clear_history_kb(),
        )

    @bot.on.message(base.PayloadMapRule({"cmd": "confirm_clear_history"}))
    async def confirm_clear_history(message: Message) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = state.active_dialog
        if dialog is None:
            await message.answer("⚠️ Нет активного диалога.", keyboard=main_menu_kb())
            return
        memory.clear_history(dialog)
        await dialogs.save(state)
        await message.answer(
            f"🧹 История диалога «{dialog.title}» очищена.",
            keyboard=main_menu_kb(),
        )

    # ── Переименование диалога ───────────────────────────────────────

    @bot.on.message(base.RegexRule(r"^/rename\s+(?P<name>.+)$"))
    async def cmd_rename(message: Message, match: tuple) -> None:
        state = await dialogs.get_state(message.from_id)
        dialog = dialogs.rename_dialog(state, state.active_dialog_id, match[0])
        if dialog is None:
            await message.answer(
                "⚠️ Укажите название: /rename Новое имя",
                keyboard=main_menu_kb(),
            )
            return
        await dialogs.save(state)
        await message.answer(
            f"✏️ Диалог переименован в «{dialog.title}».",
            keyboard=main_menu_kb(),
        )

    # ── AI-чат (catch-all для текстовых сообщений) ──────────────────

    @bot.on.message()
    async def chat(message: Message) -> None:
        await handle_chat_message(
            message,
            dialogs=dialogs,
            memory=memory,
            ai=ai,
            max_message_length=max_message_length,
            typing_enabled=typing_enabled,
            typing_speed=typing_speed,
            typing_max_seconds=typing_max_seconds,
        )


# ── Логика AI-чата ──────────────────────────────────────────────────


async def handle_chat_message(
    message: Message,
    *,
    dialogs: DialogManager,
    memory: MemoryManager,
    ai: AIService,
    max_message_length: int,
    typing_enabled: bool,
    typing_speed: int,
    typing_max_seconds: float,
) -> None:
    """Обработка текстового сообщения: контекст → Gemini → ответ."""

    # Защита от пустых сообщений
    text = normalize_user_text(message.text)
    if text is None:
        await message.answer(
            "🤔 Напишите что-нибудь текстом — я отвечу!",
            keyboard=main_menu_kb(),
        )
        return

    user_id = message.from_id
    state = await dialogs.get_state(user_id)
    dialog = state.active_dialog
    if dialog is None:  # на всякий случай
        dialog = dialogs.create_dialog(state)
        await dialogs.save(state)

    # Сохраняем сообщение пользователя до запроса — не потеряется при ошибке
    memory.add_user_message(dialog, text)

    placeholder: ThinkingPlaceholder | None = None
    stop_typing = asyncio.Event()
    typing_task: asyncio.Task | None = None

    if typing_enabled:
        placeholder = ThinkingPlaceholder(message.ctx_api, message.peer_id)
        await placeholder.start()
        typing_task = asyncio.create_task(
            typing_loop(message.ctx_api, message.peer_id, stop_typing)
        )

    try:
        context = memory.build_context(dialog)
        mode = CommunicationMode.from_str(dialog.mode)
        reply = await ai.generate_reply(context, mode)
    except AIUnavailableError:
        logger.warning("AI недоступен для пользователя %s", user_id)
        if placeholder is not None:
            await placeholder.abort()
        await message.answer(fallback_text(), keyboard=main_menu_kb())
        await dialogs.save(state)
        return
    finally:
        stop_typing.set()
        if typing_task is not None:
            await typing_task

    # Ограничение длины сообщения VK
    reply = truncate_vk(reply, max_message_length)

    # Имитация «человеческой» задержки набора
    if typing_enabled:
        delay = estimate_typing_delay(reply, typing_speed, typing_max_seconds)
        if delay > 0:
            await asyncio.sleep(delay)

    memory.add_assistant_message(dialog, reply)
    await dialogs.save(state)

    if placeholder is not None:
        await placeholder.finalize(reply, keyboard=main_menu_kb())
    else:
        await message.answer(reply, keyboard=main_menu_kb())


# ── Тексты ──────────────────────────────────────────────────────────

HELP_TEXT = (
    "❓ <b>Как пользоваться ботом</b>\n\n"
    "💬 <b>Общение</b> — просто пишите сообщение, модель ответит.\n"
    "🆕 <b>Новый диалог</b> — начните отдельную беседу с новой историей.\n"
    "📚 <b>Диалоги</b> — список ваших бесед, переключение и удаление.\n"
    "🎭 <b>Режимы</b> — помощник, программист, преподаватель,\n"
    "   бизнес-консультант или собеседник (для каждого диалога свой).\n"
    "⚙️ <b>Настройки</b> — режим, модель, очистка истории.\n\n"
    "✏️ Переименование диалога: <code>/rename Новое имя</code>\n"
    "🧹 Подсказки: память диалога — последние 100 сообщений,\n"
    "   старые удаляются автоматически."
)
