# Stream Analytics System

Базовый каркас проекта для сбора и анализа потоковых данных. 
Включает сервис генератора данных на Python и аналитическую СУБД ClickHouse, запускаемые через Docker Compose.

---

## 🏗 Архитектура каркаса

```text
[ Python Generator ]
        │  (Батчевая передача событий)
        ▼
[ ClickHouse Server ]
```

---

## ⚙️ Сервисы и порты

| Сервис | Порт | Логин / Пароль по умолчанию | Описание |
| :--- | :--- | :--- | :--- |
| **ClickHouse HTTP** | `8123` | `default` / *(без пароля)* | HTTP API & Web UI |
| **ClickHouse Native** | `9000` | `default` / *(без пароля)* | Нативный TCP интерфейс |
| **Generator** | - | - | Сервис генерации данных |

---

## 🚀 Быстрый старт

### 1. Настройка окружения
```bash
cp .env.example .env
```

### 2. Запуск контейнеров
```bash
docker compose up -d
```

### 3. Проверка статуса
```bash
docker compose ps
docker compose logs -f generator
```

### 4. Остановка
```bash
docker compose down
```

---

## 📁 Структура проекта

```text
stream-analytics/
├── .env.example              # Шаблон конфигурации
├── .gitignore                # Исключения версионного контроля
├── docker-compose.yml        # Оркестрация ClickHouse и генератора
├── README.md                 # Описание каркаса проекта
├── CONTRIBUTING.md           # Правила совместной разработки и Git Workflow
├── generator/                # Сервис генератора данных (Python)
│   ├── Dockerfile
│   └── src/
│       └── main.py
└── clickhouse/               # Инициализация ClickHouse
    └── init/                 # Каталог для будущих DDL скриптов
```
