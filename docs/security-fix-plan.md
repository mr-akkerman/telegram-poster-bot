# План исправления уязвимостей

На основе [аудита безопасности](security-audit.md).

---

## Фаза 1 — Критические и высокие (немедленно)

### Fix 1.1 — Проверка прав пользователя при добавлении канала
**Уязвимость:** #1 (CRITICAL)
**Файл:** `bot/handlers/channels.py` → `_try_add_channel()`

**Что сделать:**
- После проверки прав бота — добавить проверку `bot.get_chat_member(channel_id, message.from_user.id)`
- Пользователь должен быть `ADMINISTRATOR` или `CREATOR`
- При неудаче — сообщение «Вы не являетесь администратором этого канала»

---

### Fix 1.2 — Экранирование HTML в пользовательских строках
**Уязвимость:** #2 (HIGH)
**Файлы:** `bot/handlers/posts.py`, `bot/handlers/channels.py`

**Что сделать:**
- Добавить `from html import escape`
- Экранировать `channel_title` везде, где он подставляется в HTML-сообщения:
  - `posts.py` — publish success message
  - `posts.py` — republish success message
  - `channels.py` — channel added success message
- Экранировать `channel_username` в inline-кнопках (хотя кнопки не парсят HTML, для консистентности)

---

### Fix 1.3 — Скрыть сырые исключения
**Уязвимость:** #3 (HIGH)
**Файл:** `bot/handlers/posts.py`

**Что сделать:**
- В обоих блоках `except Exception as e` (publish и republish):
  - Логировать с `exc_info=True`
  - Показывать пользователю: «Не удалось опубликовать пост. Проверьте, что бот является администратором канала.»

---

## Фаза 2 — Средние (планово)

### Fix 2.1 — Валидация callback_data
**Уязвимость:** #4 (MEDIUM)

**Что сделать:**
- Создать утилитарную функцию:
  ```python
  def parse_callback_int(data: str, prefix: str, index: int = 1) -> int | None
  ```
- Использовать её во всех обработчиках callback
- При `None` — отвечать `callback.answer("Ошибка", show_alert=True)` и return

---

### Fix 2.2 — Лимиты на ресурсы
**Уязвимость:** #5 (MEDIUM)

**Что сделать:**
- Перед добавлением канала — проверить `SELECT COUNT(*) FROM channels WHERE user_id = ?` < 50
- Перед созданием поста — проверить `SELECT COUNT(*) FROM posts WHERE user_id = ?` < 500
- В `parse_buttons()` — ограничить максимум 5 рядов, 5 кнопок в ряду (25 итого)
- Добавить простой throttling: middleware с `TTLCache` (1 сообщение в секунду на пользователя)

---

### Fix 2.3 — Изоляция DB-соединений
**Уязвимость:** #6 (MEDIUM)

**Что сделать:**
- Изменить `DatabaseMiddleware`: создавать новое `aiosqlite.connect()` на каждый update
- Убрать `Database.conn` property
- Хранить в `Database` только `db_path`
- Соединение закрывается автоматически через `async with`

---

### Fix 2.4 — FSM-защита для forward и @username
**Уязвимости:** #7, #8 (MEDIUM)

**Что сделать:**
- Добавить FSM-состояние `AddChannel.waiting_for_input`
- Кнопка «📢 Мои каналы» → «➕ Добавить канал» → устанавливает состояние `AddChannel.waiting_for_input`
- Обработчики forward и @username привязать к этому состоянию
- Добавить regex-фильтр для @username: `r"^@[a-zA-Z][a-zA-Z0-9_]{3,31}$"`

---

## Фаза 3 — Низкие (при возможности)

### Fix 3.1 — Валидация пагинации
**Уязвимость:** #9 (LOW)

**Что сделать:** `page = max(0, int(...))` в `cb_posts_page`.

### Fix 3.2 — Персистентное FSM-хранилище
**Уязвимость:** #10 (LOW)

**Что сделать:** На Railway можно подключить Redis Add-on и использовать `RedisStorage`. Опционально для MVP.

---

## Порядок выполнения

```
Fix 1.1 (CRITICAL) → Fix 1.2 + 1.3 (HIGH) → Fix 2.1 (MEDIUM) → Fix 2.2 → Fix 2.3 → Fix 2.4 → Fix 3.1 → Fix 3.2
```

Фаза 1 — один коммит. Фаза 2 — один коммит. Фаза 3 — один коммит.
