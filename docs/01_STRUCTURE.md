# Дизайн-документ: структура проекта

**Проект:** Dara Exchange — бот обмена игрушками  
**Версия:** 1.0

---

## 1. Общие принципы

- **Монолит бота** — один процесс (polling или webhook), без микросервисов на старте.
- **Слои:** handlers → services → models/repositories. Handlers не обращаются к БД напрямую.
- **Конфигурация** — через переменные окружения (`.env`), без секретов в коде.
- **Состояние пользователя** — FSM (Finite State Machine) в памяти или Redis; критичные данные — в БД.

---

## 2. Дерево каталогов

```
kaztoys/
├── .env.example              # Шаблон переменных окружения
├── .env                      # Локальные секреты (не в git)
├── requirements.txt
├── README.md
├── ПЛАН_РАЗРАБОТКИ_БОТА.md
│
├── docs/                     # Дизайн-документы
│   ├── 01_STRUCTURE.md       # Этот файл
│   ├── 02_DATABASE.md
│   ├── 03_BUSINESS_LOGIC.md
│   └── 04_USER_STORIES.md
│
├── bot/
│   ├── __init__.py
│   ├── main.py               # Точка входа: создание Bot, Dispatcher, запуск polling/webhook
│   ├── config.py             # Загрузка настроек из os.environ / pydantic-settings
│   │
│   ├── handlers/             # Обработчики апдейтов (входящие сообщения, кнопки)
│   │   ├── __init__.py
│   │   ├── start.py          # /start, реферал, дисклеймер, видео, "Начать поиск"
│   │   ├── menu.py           # Главное меню, таймаут неактивности, рассылка новых заявок
│   │   ├── listing.py        # Создание/редактирование заявки (код→фото→категория→возраст→описание)
│   │   ├── search.py         # Опрос поиска, показ по одной, Дальше, Изменить параметры
│   │   ├── response.py       # Отклик: выбор игрушки, создание отклика, отправка
│   │   ├── matches.py        # Просмотр откликов по заявке, выбор отклика, мэтч, подтверждение сделки
│   │   ├── subscription.py   # Моя подписка, оплата, подключение
│   │   └── support.py        # Связаться с поддержкой
│   │
│   ├── keyboards/            # Сборка Reply/Inline клавиатур
│   │   ├── __init__.py
│   │   ├── common.py         # "В главное меню", "Отмена" и т.д.
│   │   ├── menu.py           # Кнопки главного меню
│   │   ├── categories.py     # Категории и возраст (справочники v4)
│   │   └── districts.py      # Районы Астаны
│   │
│   ├── services/             # Бизнес-логика, работа с БД
│   │   ├── __init__.py
│   │   ├── user.py           # Регистрация, профиль, confirmed_deals, поисковые фильтры
│   │   ├── listing.py        # CRUD заявок, генерация кода, валидация
│   │   ├── response.py       # Создание отклика, привязка к заявке
│   │   ├── search.py         # Фильтрация заявок (категория, возраст, район), пагинация "по одной"
│   │   ├── match.py          # Выбор отклика, создание мэтча, подтверждение сделки
│   │   └── subscription.py   # Проверка подписки, создание/продление
│   │
│   ├── models/               # ORM-модели (SQLAlchemy или аналоги)
│   │   ├── __init__.py
│   │   ├── base.py           # Base, session factory
│   │   ├── user.py
│   │   ├── listing.py
│   │   ├── response.py
│   │   ├── match.py
│   │   └── subscription.py
│   │
│   ├── repositories/         # (Опционально) Доступ к БД поверх моделей
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── listing.py
│   │   └── ...
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── db.py             # Инъекция сессии БД в контекст
│   │   ├── inactivity.py     # Таймер 10 мин → сброс в главное меню
│   │   └── throttling.py     # Защита от флуда
│   │
│   ├── filters/              # Кастомные фильтры для роутеров
│   │   ├── __init__.py
│   │   ├── subscription.py  # "Есть активная подписка"
│   │   └── state.py         # "Пользователь в главном меню"
│   │
│   └── texts/                # Тексты сообщений бота (удобно вынести для правок)
│       ├── __init__.py
│       ├── onboarding.py
│       ├── menu.py
│       ├── listing.py
│       ├── search.py
│       └── errors.py
│
├── migrations/               # Alembic (или аналог) — миграции БД
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── assets/                   # Статические файлы бота
│   └── video_instruction.mp4 # Видео-инструкция для онбординга
│
└── tests/
    ├── conftest.py           # Pytest fixtures (session, bot mock)
    ├── test_services/
    │   ├── test_listing.py
    │   └── test_search.py
    └── test_handlers/
        └── ...
```

---

## 3. Назначение слоёв

| Слой | Назначение |
|------|------------|
| **handlers** | Приём апдейтов, вызов сервисов, отправка сообщений и клавиатур. Минимум логики. |
| **services** | Правила бизнеса: создание заявки, отклика, мэтча; проверка подписки; выбор следующей заявки в поиске. |
| **models** | Описание таблиц и связей. Работа с БД через ORM. |
| **repositories** | Опционально: сложные выборки, переиспользуемые запросы. |
| **keyboards** | Только сборка клавиатур по контексту (меню, категории, одна заявка и т.д.). |
| **texts** | Все строки, которые видит пользователь — для удобной локализации и правок. |
| **middlewares** | Сквозная логика: сессия БД, таймаут неактивности, логирование. |
| **filters** | Условия для роутеров: «пользователь с подпиской», «состояние = главное меню». |

---

## 4. Зависимости (requirements.txt)

```
# Ядро бота
aiogram>=3.4.0
aiohttp>=3.9.0

# БД
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0

# Конфиг и окружение
pydantic-settings>=2.0.0
python-dotenv>=1.0.0

# Утилиты
structlog>=24.0.0
```

(При выборе другой БД — заменить `asyncpg` на нужный драйвер.)

---

## 5. Точка входа

**`bot/main.py`** (упрощённо):

1. Загрузка `config` из окружения.
2. Инициализация логгера.
3. Создание `Bot`, `Dispatcher`.
4. Подключение роутеров из `handlers` (start, menu, listing, search, response, matches, subscription, support).
5. Регистрация middlewares (DB, inactivity, throttling).
6. Запуск: `dp.start_polling(bot)` или регистрация webhook.

**`config.py`** — объект с полями: `BOT_TOKEN`, `DATABASE_URL`, `REFERRAL_PARAM`, пути к видео, текст дисклеймера и т.д.

---

## 6. Переменные окружения (.env.example)

```ini
BOT_TOKEN=123:ABC...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/kaztoys
REFERRAL_PARAM=ref
SUPPORT_CONTACT=@support_username
VIDEO_INSTRUCTION_PATH=assets/video_instruction.mp4
INACTIVITY_MINUTES=10
```

---

## 7. Связь с другими дизайн-документами

- **02_DATABASE.md** — структура таблиц, используемых в `models/` и `services/`.
- **03_BUSINESS_LOGIC.md** — сценарии и FSM, реализуемые в `handlers/` и `services/`.
- **04_USER_STORIES.md** — что видит пользователь на каждом шаге; соответствует роутам в `handlers/` и текстам в `texts/`.
