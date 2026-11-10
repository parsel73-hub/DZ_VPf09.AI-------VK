# 🤖 AI-ассистент ВКонтакте

Интеллектуальный AI-помощник внутри бота ВКонтакте на **Python + VKBottle** с интеграцией **Gemini** через **ProxyAPI.ru**.

## Возможности

- 💬 **Многодиалоговый режим** — неограниченное число независимых диалогов (до 50) с отдельной историей, названием и режимом общения
- 🧠 **Краткосрочная память** — до 100 последних сообщений на диалог, старые удаляются автоматически
- 🎭 **5 режимов общения** (system prompt'ы): обычный помощник, программист, преподаватель, бизнес-консультант, дружелюбный собеседник
- 🤖 **Gemini через ProxyAPI** — официальный `google-genai` SDK, ключ и оплата в рублях, без VPN
- 💾 **JSON-хранилище** — отдельный файл `users/{user_id}.json` на пользователя, без БД
- ⌨️ **Имитация набора** — статус «печатает…», сообщение «⏳ Бот думает…» с плавным превращением в ответ
- 📱 **Полный интерфейс на VK-клавиатурах** — меню, списки диалогов, настройки, подтверждения действий

## Архитектура

```
VK Long Poll (vkbottle)
        │  message_new (текст / payload-кнопка)
        ▼
handlers/message_handlers.py     ← слой VK: только оркестрация, ноль AI-логики
        │
        ▼
services/                        ← бизнес-слой
  DialogManager ──► MemoryManager ──► AIService ──► google-genai SDK
        │                                  │            │
        ▼                                  ▼            ▼
storage/json_storage.py            ProxyAPI.ru    /v1beta/models/{model}
  users/{id}.json                  (x-goog-api-key)  :generateContent
```

**Разделение ответственности:**

| Слой | Модуль | Зона ответственности |
|---|---|---|
| VK | `handlers/`, `keyboards/` | Приём событий, клавиатуры, форматирование ответов |
| Бизнес | `services/dialog_manager.py`, `services/memory_manager.py` | Диалоги, режимы, история, контекст |
| AI | `services/ai_service.py` | Gemini, system prompt, ретраи, fallback |
| Хранилище | `storage/json_storage.py` | Атомарная запись JSON, блокировки |
| Конфигурация | `config/settings.py`, `config/prompts.py` | `.env`, системные промпты |

## Структура проекта

```
├── bot.py                        # точка входа: сборка компонентов + Long Poll
├── requirements.txt
├── .env.example                  # шаблон конфигурации
├── config/
│   ├── settings.py               # Settings из .env (frozen dataclass + validate)
│   └── prompts.py                # COMMUNICATION_MODES — 5 system prompt'ов
├── models/
│   └── entities.py               # ChatMessage, Dialog, UserState, CommunicationMode
├── storage/
│   └── json_storage.py           # JsonUserStorage: async, lock, атомарная запись
├── services/
│   ├── ai_service.py             # AIService: Gemini через ProxyAPI + ретраи
│   ├── dialog_manager.py         # DialogManager: CRUD диалогов, переключение
│   └── memory_manager.py         # MemoryManager: история, обрезка, контекст
├── keyboards/
│   └── kb.py                     # VK-клавиатуры (меню, диалоги, режимы, настройки)
├── handlers/
│   └── message_handlers.py       # Хендлеры команд, кнопок и AI-чата
└── utils/
    ├── logger.py                 # Настройка логирования
    ├── text.py                   # normalize_user_text, truncate_vk
    ├── typing.py                 # set_typing, ThinkingPlaceholder, задержки
    └── errors.py                 # BotError, AIUnavailableError, fallback_text
```

## Установка

### 1. Зависимости

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 2. Токен группы ВКонтакте

1. Создайте сообщество ВК → *Управление → Настройки → Доступ к API*:
   - **Сервер доступа**: включите Long Poll API, версия **5.199**
   - **Тип событий**: включите *Получение событий с сервера*
   - **События**: отметьте **«Новое сообщение»**
2. *Работа с ботом → Long Poll API → Key* — скопируйте токен группы.
3. Разрешите сообщения сообщества для всех пользователей.

### 3. Ключ ProxyAPI

1. Зарегистрируйтесь в [консоли ProxyAPI](https://console.proxyapi.ru/) и подтвердите почту.
2. Создайте ключ в разделе **«Ключи API»** (начинается с `sk-`, показывается один раз).
3. Пополните баланс — пока он пуст, запросы вернут ошибку.

### 4. Конфигурация

```powershell
Copy-Item .env.example .env
# отредактируйте .env: VK_GROUP_TOKEN и PROXYAPI_KEY — обязательны
```

## Конфигурация (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `VK_GROUP_TOKEN` | — | Токен группы ВК (**обязательно**) |
| `PROXYAPI_KEY` | — | Ключ ProxyAPI (**обязательно**) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Модель (список: proxyapi.ru/models/google) |
| `PROXYAPI_BASE_URL` | `https://api.proxyapi.ru` | Базовый адрес провайдера |
| `GOOGLE_API_VERSION` | `v1beta` | Версия формата Google API |
| `GEMINI_TEMPERATURE` | `0.7` | Температура генерации |
| `GEMINI_MAX_OUTPUT_TOKENS` | `2048` | Лимит токенов ответа |
| `MAX_HISTORY` | `100` | Сообщений в истории диалога |
| `USERS_DIR` | `users` | Папка JSON-файлов пользователей |
| `MAX_MESSAGE_LENGTH` | `4096` | Лимит длины сообщения VK |
| `TYPING_ENABLED` | `true` | Имитация набора и «бот думает…» |
| `TYPING_SPEED` | `40` | Символов в секунду при оценке задержки |
| `TYPING_MAX_SECONDS` | `8` | Максимальная пауза «печати» |
| `REQUEST_TIMEOUT_SEC` | `60` | Таймаут запроса к Gemini |
| `REQUEST_RETRIES` | `2` | Повторы при ошибках API/сети |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

## Запуск

```powershell
.\venv\Scripts\python.exe bot.py
```

Остановка — `Ctrl+C`. Состояние Long Poll (ts) сохраняется в `.vkbottle/`, старые события после перезапуска не обрабатываются.

## Использование

| Действие | Как |
|---|---|
| Начать общение | Просто написать сообщение текстом |
| Главное меню | `/start` или кнопка с любой экранной формы |
| Справка | `/help` или кнопка «❓ Помощь» |
| Новый диалог | Кнопка «🆕 Новый диалог» |
| Список диалогов | Кнопка «📚 Диалоги» → переключение ✅ / удаление 🗑 |
| Переименовать | `/rename Новое имя` (активного диалога) |
| Сменить режим | Кнопка «🎭 Сменить режим» — влияет **только на текущий диалог** |
| Настройки | Кнопка «⚙️ Настройки»: режим, модель, очистка истории |

### Режимы общения

| Ключ | Режим | System prompt (кратко) |
|---|---|---|
| `assistant` | 🤖 Обычный помощник | Дружелюбно, кратко, по-русски |
| `programmer` | 💻 Программист | Код, отладка, best practices, markdown |
| `teacher` | 📚 Преподаватель | Пошагово, аналогии, учит думать |
| `business` | 📊 Бизнес-консультант | Структурно, деловой стиль, цифры |
| `friend` | 😊 Дружелюбный собеседник | Разговорный стиль, поддержка |

Тексты промптов редактируются в `config/prompts.py` — код менять не нужно.

## Формат хранения (users/{user_id}.json)

```json
{
  "user_id": 123456789,
  "dialogs": {
    "a1b2c3d4e5f6": {
      "id": "a1b2c3d4e5f6",
      "title": "Диалог 1",
      "mode": "programmer",
      "messages": [
        { "role": "user", "content": "Привет", "timestamp": "2026-11-10T07:00:00+00:00" },
        { "role": "assistant", "content": "Привет! Чем помочь?", "timestamp": "2026-11-10T07:00:05+00:00" }
      ]
    }
  },
  "active_dialog_id": "a1b2c3d4e5f6",
  "settings": {}
}
```

Запись атомарная (временный файл → `os.replace`), параллельные обращения к одному пользователю сериализуются через `asyncio.Lock`. Повреждённый JSON восстанавливается автоматически (пользователь получает новый диалог).

## Запрос к Gemini (ядро AIService)

```python
response = await self._client.aio.models.generate_content(
    model="gemini-3.5-flash",
    contents=[Content(role="user", parts=[Part(text="Привет!")])],
    config=GenerateContentConfig(
        system_instruction=COMMUNICATION_MODES["programmer"]["system_prompt"],
        temperature=0.7,
        max_output_tokens=2048,
    ),
)
```

Клиент настраивается один раз: `HttpOptions(base_url="https://api.proxyapi.ru", api_version="v1beta")` — SDK сам дописывает путь `/v1beta/models/{model}:generateContent` и передаёт ключ заголовком `x-goog-api-key` (формат ProxyAPI для Google SDK).

При ошибке API/сети выполняется до `REQUEST_RETRIES` попыток с backoff; при полном исчерпании пользователь получает fallback-сообщение, переписка не теряется.

## Проверка

Сборка без внешних зависимостей (импорт модулей, регистрация 17 хендлеров, roundtrip JSON, клавиатуры, лимиты):

```powershell
.\venv\Scripts\python.exe -c "import handlers.message_handlers; print('OK')"
```

## Рекомендации по масштабированию

- **Другие модели/вендоры** — вынести интерфейс `LLMProvider`; модели OpenAI/DeepSeek доступны тем же ключом на `https://api.proxyapi.ru/v1`
- **Ограничение контекста в токенах** — использовать `count_tokens` перед отправкой (тот же путь `/v1beta`)
- **Несколько инстансов бота** — заменить `JsonUserStorage` за интерфейсом на Redis/S3 (бизнес-логика не изменится)
- **Стриминг ответов** — `generate_content_stream` + периодический `messages.edit`
- **Очередь сообщений на пользователя** — защита от гонки при быстрых повторных сообщениях
- **Webhook вместо Long Poll** — `bot.setup_webhook()` для продакшена за HTTPS-балансировщиком

## Технологии

- [Python](https://python.org) 3.12 (asyncio, dataclasses, type hints)
- [VKBottle 4.11](https://vkbottle.rtfd.io) — асинхронный фреймворк VK API
- [Google Gen AI SDK](https://googleapis.github.io/python-genai/) — `google-genai`
- [ProxyAPI.ru](https://proxyapi.ru/docs/gemini-api) — доступ к Gemini из России, оплата в рублях
