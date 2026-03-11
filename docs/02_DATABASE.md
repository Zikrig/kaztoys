# Дизайн-документ: база данных

**Проект:** Dara Exchange  
**Версия:** 1.0

---

## 1. Общие решения

- **СУБД:** PostgreSQL (рекомендуется) или SQLite для разработки.
- **Драйвер:** async (asyncpg для PostgreSQL, aiosqlite для SQLite).
- **ORM:** SQLAlchemy 2.x (async).
- **Миграции:** Alembic.
- **Уникальные коды заявок/откликов:** общее пространство кодов (одна последовательность или отдельные таблицы с уникальным полем `code`), чтобы коды заявок и откликов не повторялись.

---

## 2. ER-диаграмма (сущности и связи)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   users     │───1:N─│  listings   │───1:N─│  responses  │
└─────────────┘       └─────────────┘       └─────────────┘
       │                     │                     │
       │                     │                     │
       │               listing_id                  │
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                      ┌──────┴──────┐
                      │   matches   │  (мэтч = выбранный отклик по заявке)
                      └──────┬──────┘
                             │
                    ┌────────┴────────┐
                    │ match_confirmations │ (подтверждение сделки каждым участником)
                    └─────────────────┘

┌─────────────┐       ┌─────────────────┐
│   users     │───1:N─│  subscriptions  │
└─────────────┘       └─────────────────┘

┌─────────────┐       ┌─────────────────┐
│   users     │───1:1─│ search_filters  │  (сохранённые параметры поиска)
└─────────────┘       └─────────────────┘
```

---

## 3. Таблицы

### 3.1 `users`

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | Внутренний ID |
| telegram_id | BIGINT UNIQUE NOT NULL | Telegram user id |
| username | VARCHAR(255) | @username |
| first_name | VARCHAR(255) | Имя в Telegram |
| phone | VARCHAR(50) | Номер телефона (если пользователь указал) |
| confirmed_deals | INT DEFAULT 0 | Количество подтверждённых сделок |
| referral_from_id | BIGINT FK(users.id) NULL | Кто привёл (если вход по рефералке) |
| created_at | TIMESTAMPTZ | Первый контакт с ботом |
| updated_at | TIMESTAMPTZ | Последнее обновление |

**Индексы:** `telegram_id` (уникальный), при необходимости `referral_from_id`.

---

### 3.2 `listings` (заявки)

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | Внутренний ID |
| code | VARCHAR(20) UNIQUE NOT NULL | Уникальный код (например "12345") — общее пространство с откликами |
| user_id | BIGINT FK(users.id) NOT NULL | Автор заявки |
| photo_file_id | VARCHAR(255) | file_id фото в Telegram (для повторной отправки без загрузки) |
| category | VARCHAR(100) NOT NULL | Категория (из справочника v4) |
| age_group | VARCHAR(50) NOT NULL | Возраст: 0-2, 3-5, 6-8, 9-12, any |
| district | VARCHAR(100) | Район Астаны (может быть NULL = любой) |
| description | TEXT NOT NULL | Описание и на что менять/продать |
| status | VARCHAR(20) NOT NULL | open \| closed |
| created_at | TIMESTAMPTZ | Время создания |
| updated_at | TIMESTAMPTZ | Время последнего изменения |

**Индексы:** `code` UNIQUE, `user_id`, `status`, `created_at` (для сортировки в поиске).  
**Составной индекс для поиска:** `(status, category, age_group, district, created_at)` — для выборки открытых заявок по фильтрам с сортировкой по дате.

**Справочники (константы в коде или отдельные таблицы):**
- Категории: `scooters_bikes`, `for_babies`, `dolls_figures`, `cars_guns`, `other`
- Возраст: `0_2`, `3_5`, `6_8`, `9_12`, `any`
- Районы: список Астаны (отдельная таблица `districts` опционально).

---

### 3.3 `responses` (отклики)

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | Внутренний ID |
| code | VARCHAR(20) UNIQUE NOT NULL | Уникальный код отклика (общее пространство с заявками) |
| listing_id | BIGINT FK(listings.id) NOT NULL | Заявка, на которую отклик |
| user_id | BIGINT FK(users.id) NOT NULL | Автор отклика |
| photo_file_id | VARCHAR(255) | Фото игрушки в отклике |
| description | TEXT NOT NULL | Описание и сообщение продавцу |
| chosen | BOOLEAN DEFAULT FALSE | Выбран ли этот отклик владельцем заявки (создан мэтч) |
| created_at | TIMESTAMPTZ | Время создания |

**Индексы:** `code` UNIQUE, `listing_id`, `user_id`, `chosen`.

---

### 3.4 `matches` (мэтчи — выбор отклика)

Один выбранный отклик = один мэтч. Обе стороны участвуют в одной записи.

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | Внутренний ID |
| listing_id | BIGINT FK(listings.id) NOT NULL | Заявка |
| response_id | BIGINT FK(responses.id) UNIQUE NOT NULL | Выбранный отклик (у отклика может быть только один мэтч) |
| listing_owner_id | BIGINT FK(users.id) NOT NULL | Владелец заявки |
| response_owner_id | BIGINT FK(users.id) NOT NULL | Автор отклика |
| status | VARCHAR(20) NOT NULL | pending \| both_confirmed \| one_cancelled |
| created_at | TIMESTAMPTZ | Когда отклик был выбран |

**Индексы:** `listing_id`, `response_id` UNIQUE, `listing_owner_id`, `response_owner_id`, `status`.

---

### 3.5 `match_confirmations` (подтверждение сделки каждым участником)

Можно хранить подтверждения в одной таблице: кто и по какому мэтчу подтвердил.

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | |
| match_id | BIGINT FK(matches.id) NOT NULL | Мэтч |
| user_id | BIGINT FK(users.id) NOT NULL | Кто подтвердил (владелец заявки или отклика) |
| action | VARCHAR(20) NOT NULL | confirmed \| cancelled |
| created_at | TIMESTAMPTZ | Время нажатия |

**Уникальность:** один пользователь — одно подтверждение на один match: UNIQUE(match_id, user_id).  
**Альтернатива:** хранить в `matches` два поля `listing_owner_confirmed`, `response_owner_confirmed` (boolean). Тогда отдельная таблица не обязательна.

**Рекомендация:** два поля в `matches`: `listing_owner_confirmed BOOLEAN DEFAULT FALSE`, `response_owner_confirmed BOOLEAN DEFAULT FALSE`. При обоих TRUE — статус мэтча `both_confirmed`, обоим пользователям +1 к `confirmed_deals`.

---

### 3.6 `subscriptions`

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | |
| user_id | BIGINT FK(users.id) NOT NULL | Пользователь |
| started_at | TIMESTAMPTZ NOT NULL | Начало подписки |
| expires_at | TIMESTAMPTZ NOT NULL | Окончание (например +14 дней) |
| created_at | TIMESTAMPTZ | Запись создана |

**Индексы:** `user_id`, `expires_at`. Активная подписка: `expires_at > NOW()`.

---

### 3.7 `search_filters` (сохранённые параметры поиска по пользователю)

Один набор фильтров на пользователя (при повторном опросе — перезапись).

| Поле | Тип | Описание |
|------|-----|----------|
| user_id | BIGINT FK(users.id) PRIMARY KEY | Пользователь |
| category | VARCHAR(100) | Категория или "all" |
| age_group | VARCHAR(50) | 0-2, 3-5, 6-8, 9-12, any |
| district | VARCHAR(100) | Район или "any" |
| updated_at | TIMESTAMPTZ | Когда сохранены |

---

### 3.8 `search_notifications` (уведомления о новых заявках — второй этап)

Когда пользователь долистал поиск до конца, сохраняем его фильтры для пуша при появлении новой подходящей заявки.

| Поле | Тип | Описание |
|------|-----|----------|
| id | BIGSERIAL PK | |
| user_id | BIGINT FK(users.id) NOT NULL | Кому слать уведомление |
| category | VARCHAR(100) | Фильтр категории |
| age_group | VARCHAR(50) | Фильтр возраста |
| district | VARCHAR(100) | Фильтр района |
| created_at | TIMESTAMPTZ | Когда подписался на уведомления |

При появлении новой заявки — выборка пользователей из `search_notifications`, у которых фильтры совпадают с полями заявки, и отправка им сообщения «Новая игрушка в категории …» + кнопка «Посмотреть». Можно затем удалять запись или помечать «отправлено для listing_id», чтобы не слать повторно одно и то же.

---

## 4. Генерация уникальных кодов

- Заявки и отклики не должны иметь одинаковых кодов.
- **Вариант А:** одна таблица `codes` с полем `code` (VARCHAR UNIQUE), при создании заявки/отклика вставляем новый код (например случайный 5–6 знаков с проверкой уникальности).
- **Вариант Б:** один счётчик в БД (например таблица `sequences` с полем `next_code`) и форматировать как строку с паддингом (00001, 00002, …).
- **Вариант В:** UUID короткий или nanoid — гарантированно уникально без обращения к БД для проверки.

Рекомендация: **Вариант А** — случайный короткий код (цифры/буквы), при коллизии — повторить генерацию.

---

## 5. Жизненный цикл заявки и отклика

1. Пользователь создаёт заявку → `listings` (status=open).
2. Другой пользователь создаёт отклик → `responses` (chosen=false).
3. Владелец заявки нажимает «Выбрать» → создаётся `matches`, у отклика `chosen=true`.
4. Оба получают «ПОМНИТЕ???» и кнопки «Подтвердить сделку» / «Сделка не состоялась».
5. Подтверждения пишем в `matches` (два булевых поля или таблица подтверждений). При обоих «Подтвердить» → status=both_confirmed, у обоих users +1 к confirmed_deals.
6. Закрытие заявки → listings.status=closed. Отклики по этой заявке не удаляем физически (для истории), но в интерфейсе заявка не показывается. При необходимости каскадно помечать связанные мэтчи.

---

## 6. Индексы для поиска заявок (по одной)

Запрос: открытые заявки по (category, age_group, district), сортировка по created_at DESC, лимит 1 и смещение по странице.

- Составной индекс: `(status, category, age_group, district, created_at DESC)`.
- Для «Все категории» — запрос без фильтра по category или с IN (все категории).
- «Любой район» — district IS NULL или district = 'any' в фильтре пользователя не учитываем в WHERE по district.

---

## 7. Связь с кодом

- **models/** — классы SQLAlchemy, соответствующие таблицам выше.
- **services/** — все запросы (создание заявки, отклика, мэтча; выбор следующей заявки в поиске; проверка подписки) используют эти модели и сессию из middleware.

Подробная бизнес-логика и сценарии — в **03_BUSINESS_LOGIC.md**.
