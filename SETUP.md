# Инструкция по запуску проекта

## Требования

- Python 3.10+
- PostgreSQL 12+
- Git

---

## Шаг 1: Клонить репозиторий

```bash
git clone <repository-url>
cd Flask_Project
```

---

## Шаг 2: Создать виртуальное окружение

**На Windows (PowerShell):**
```bash
python -m venv dev_env
.\dev_env\Scripts\Activate.ps1
```

**На Linux/macOS:**
```bash
python3 -m venv dev_env
source dev_env/bin/activate
```

---

## Шаг 3: Установить зависимости

```bash
pip install -r requirements.txt
```

---

## Шаг 4: Настроить переменные окружения

1. Создай файл `.env` в корне проекта:
```bash
cp .env.example .env  # если существует пример
```

2. Отредактируй `.env` с актуальными данными:
```env
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=db_name
```

⚠️ **ВАЖНО:** Никогда не коммитьте `.env` в гит!

---

## Шаг 5: Создать БД (если её ещё нет)

```bash
# Подключись к PostgreSQL
psql -U postgres

# Создай БД
CREATE DATABASE vkr_agata;

# Выход
\q
```

---

## Шаг 6: Применить миграции

```bash
flask db upgrade
```

Это создаст все необходимые таблицы в БД.

---

## Шаг 7: Запустить приложение

```bash
python main.py
```

Приложение будет доступно по адресу: **http://127.0.0.1:3000**

---

## Проверка корректности

### 1. Проверить что сервер работает:
```bash
curl http://127.0.0.1:3000/
# Должен вернуть HTML страницы
```

### 2. Проверить API:
```bash
curl -X POST http://127.0.0.1:3000/api/start_session \
  -H "Content-Type: application/json" \
  -d '{"visitor_id":"test-123"}'
# Должен вернуть session_id
```

### 3. Проверить БД:
```bash
psql -U postgres -d vkr_agata -c "SELECT * FROM visitors;"
# Должна вернуть данные или пустую таблицу
```

---

## Структура проекта

```
Flask_Project/
├── application.py         # Инициализация Flask приложения
├── main.py               # Точка входа (запуск на порту 3000)
├── config.py             # Конфигурация (БД, окружение)
├── requirements.txt      # Зависимости
├── .env                  # Переменные окружения (НЕ в гите!)
├── .env.example          # Пример конфига
├── .gitignore            # Что не коммитить
│
├── Controllers/
│   ├── MainController.py      # Маршруты для HTML
│   └── TrackingController.py  # API для аналитики (/api/*)
│
├── Models/
│   ├── Visitor.py       # Таблица посетителей
│   ├── Session.py       # Таблица сессий
│   ├── Event.py         # Таблица событий
│   └── __init__.py
│
├── Templates/
│   └── index.html       # Главная страница
│
├── Static/
│   └── js/
│       └── tracking.js  # Скрипт аналитики для клиента
│
├── migrations/          # Миграции БД (Alembic)
│   ├── versions/
│   ├── alembic.ini
│   └── env.py
│
└── dev_env/            # Виртуальное окружение (НЕ в гите!)
```

---

## Полезные команды

### Создать новую миграцию (при изменении моделей):
```bash
flask db migrate -m "Описание изменений"
flask db upgrade
```

### Откатить миграцию:
```bash
flask db downgrade
```

### Просмотреть историю миграций:
```bash
flask db history
```

### Запустить с логированием SQL:
```python
# В config.py измени:
'echo': True  # логирует все SQL запросы
```

---

## Возможные проблемы

### PyError: подключение к БД не работает
```
✅ Проверь что PostgreSQL запущен
✅ Проверь параметры в .env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD)
✅ Проверь что БД создана: psql -l
```

### ModuleNotFoundError: No module named 'flask'
```
✅ Активируй виртуальное окружение
✅ Переустанови зависимости: pip install -r requirements.txt
```

### Миграция падает с ошибкой
```
✅ Синхронизируй БД: flask db stamp head
✅ Откати все миграции: flask db downgrade base
✅ Примени заново: flask db upgrade
```

### Port 3000 уже в использовании
```python
# В main.py измени:
app.run(debug=True, port=3001, host='127.0.0.1')
```

---

## Разработка

### Для изменения код:
1. Код перезагружается автоматически (debug mode включен)
2. Проверяй консоль Flask на ошибки

### Перед коммитом:
```bash
# Убедись что .env не в индексе
git status
# НЕ должно быть .env в списке

# Коммит
git add .
git commit -m "Описание изменений"
```

---

## Контакты

Если возникли проблемы — напиши в чат проекта или создай Issue.
