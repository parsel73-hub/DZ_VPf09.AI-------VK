"""Асинхронное хранилище пользователей на JSON-файлах.

Каждый пользователь хранится в ``users/{user_id}.json``.
Поддерживается параллельный доступ через lock-матрицу.
Запись — атомарная (через временный файл).
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from aiofiles import open as async_open
from aiofiles.os import replace, makedirs

from models.entities import UserState


class JsonUserStorage:
    """Хранение UserState в JSON-файлах с асинхронным доступом."""

    def __init__(self, users_dir: str) -> None:
        self._users_dir = Path(users_dir)
        self._locks: dict[int, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    # ── Публичные методы ────────────────────────────────────────────

    async def ensure_dir(self) -> None:
        """Создаёт директорию users/, если не существует."""
        async with self._global_lock:
            await makedirs(self._users_dir, exist_ok=True)

    async def load(self, user_id: int) -> UserState | None:
        """Загружает состояние пользователя.

        Возвращает ``None``, если файл отсутствует.
        """
        async with self._lock_for(user_id):
            path = self._file_path(user_id)
            if not path.exists():
                return None
            try:
                async with async_open(path, "r", encoding="utf-8") as f:
                    text = await f.read()
                raw = json.loads(text)
                return UserState.from_dict(raw)
            except (json.JSONDecodeError, KeyError):
                # Повреждённый файл — создаём заново
                return None

    async def save(self, state: UserState) -> None:
        """Сохраняет состояние пользователя. Запись атомарная."""
        async with self._lock_for(state.user_id):
            path = self._file_path(state.user_id)
            data = state.to_dict()
            text = json.dumps(data, ensure_ascii=False, indent=2)
            await self._atomic_write(path, text)

    async def user_exists(self, user_id: int) -> bool:
        """Проверка наличия файла состояния."""
        return self._file_path(user_id).exists()

    async def list_user_files(self) -> list[int]:
        """Возвращает list[int] — идентификаторы пользователей."""
        if not self._users_dir.exists():
            return []
        return [
            int(p.stem)
            for p in self._users_dir.iterdir()
            if p.is_file() and p.suffix == ".json"
        ]

    # ── Внутренние методы ───────────────────────────────────────────

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        """Возвращает lock для конкретного пользователя."""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    def _file_path(self, user_id: int) -> Path:
        return self._users_dir / f"{user_id}.json"

    async def _atomic_write(
        self, path: Path, content: str
    ) -> None:
        """Атомарная запись: временный файл → переименование."""
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._users_dir), suffix=".tmp"
        )
        try:
            async with async_open(fd, "w", encoding="utf-8") as f:
                await f.write(content)
            await replace(tmp_path, path)
        except BaseException:
            # При ошибке удаляем временный файл
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
            raise
