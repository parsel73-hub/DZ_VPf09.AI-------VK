"""Менеджер диалогов: создание, переключение, переименование, удаление.

Работает поверх JsonUserStorage и инкапсулирует всю бизнес-логику
многодиалогового режима.
"""

from __future__ import annotations

import logging
import uuid

from models.entities import CommunicationMode, Dialog, UserState
from storage.json_storage import JsonUserStorage

logger = logging.getLogger(__name__)

MAX_DIALOGS_PER_USER = 50


class DialogManager:
    """CRUD-операции с диалогами пользователя."""

    def __init__(self, storage: JsonUserStorage) -> None:
        self._storage = storage

    # ── Загрузка / создание состояния ────────────────────────────────

    async def get_state(self, user_id: int) -> UserState:
        """Возвращает состояние пользователя, создавая его при необходимости.

        Новому пользователю сразу создаётся первый диалог,
        чтобы бот был готов к общению «из коробки».
        """
        state = await self._storage.load(user_id)
        if state is None:
            state = UserState(
                user_id=user_id,
                settings={"created_with_model": None},
            )
            self._create_dialog_obj(state)
            await self._storage.save(state)
            logger.info("Создано состояние пользователя %s", user_id)
        elif not state.dialogs:
            # Повреждённый/пустой файл — восстанавливаем диалог
            self._create_dialog_obj(state)
            await self._storage.save(state)
        return state

    async def save(self, state: UserState) -> None:
        """Сохраняет изменённое состояние."""
        await self._storage.save(state)

    # ── Операции с диалогами ─────────────────────────────────────────

    def create_dialog(
        self,
        state: UserState,
        mode: CommunicationMode = CommunicationMode.ASSISTANT,
    ) -> Dialog:
        """Создаёт новый диалог и делает его активным.

        Возвращает None, если достигнут лимит диалогов.
        """
        if len(state.dialogs) >= MAX_DIALOGS_PER_USER:
            return None  # type: ignore[return-value]
        dialog = self._create_dialog_obj(state, mode)
        return dialog

    def _create_dialog_obj(
        self,
        state: UserState,
        mode: CommunicationMode = CommunicationMode.ASSISTANT,
    ) -> Dialog:
        """Внутреннее создание диалога + активация."""
        dialog_id = uuid.uuid4().hex[:12]
        number = len(state.dialogs) + 1
        dialog = Dialog(
            id=dialog_id,
            title=f"Диалог {number}",
            mode=mode.value,
        )
        state.dialogs[dialog_id] = dialog
        state.active_dialog_id = dialog_id
        return dialog

    def switch_dialog(self, state: UserState, dialog_id: str) -> Dialog | None:
        """Переключает активный диалог.

        Меняются: активный контекст, история и system prompt
        (берётся из mode нового диалога при следующем запросе).
        """
        dialog = state.dialogs.get(dialog_id)
        if dialog is None:
            return None
        state.active_dialog_id = dialog_id
        return dialog

    def rename_dialog(
        self, state: UserState, dialog_id: str, title: str
    ) -> Dialog | None:
        """Переименовывает диалог. Пустые имена отбрасываются."""
        dialog = state.dialogs.get(dialog_id)
        if dialog is None or not title.strip():
            return None
        dialog.title = title.strip()[:80]
        return dialog

    def delete_dialog(self, state: UserState, dialog_id: str) -> bool:
        """Удаляет диалог. Если удалялся активный — переключает на другой.

        Последний диалог удалить нельзя: вместо этого он очищается
        через clear_history в менеджере памяти.
        """
        if dialog_id not in state.dialogs or len(state.dialogs) <= 1:
            return False
        del state.dialogs[dialog_id]
        if state.active_dialog_id == dialog_id:
            state.active_dialog_id = next(iter(state.dialogs))
        return True

    def set_mode(
        self, state: UserState, mode: CommunicationMode
    ) -> Dialog | None:
        """Меняет режим общения ТЕКУЩЕГО диалога.

        Новый system prompt применяется только к активному диалогу,
        остальные диалоги сохраняют свой режим.
        """
        dialog = state.active_dialog
        if dialog is None:
            return None
        dialog.mode = mode.value
        return dialog

    def list_dialogs(self, state: UserState) -> list[Dialog]:
        """Все диалоги пользователя (активный — первым не выделяем)."""
        return list(state.dialogs.values())
