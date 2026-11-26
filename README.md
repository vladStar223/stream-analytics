# Боевая телеметрия MMORPG

Python-генератор записывает историю и живые события персонажей батчами в ClickHouse. Superset, JupyterLab и веб-интерфейс читают одну базу. Состав сервисов и HTTP-управление генератором адаптированы из [примера преподавателя](https://github.com/theApsil/RealTime-AnalyticsPlatform/tree/fa8633f1877f7521572ee03bc85d13b1a26e21d8).

```text
generator → ClickHouse → Superset / JupyterLab / UI
               └─ hourly_realm_activity
```

## Запуск

На Windows в каталоге проекта с запущенным Docker Desktop выполните:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build
docker compose ps
docker compose logs --tail 10 generator
```

| Сервис | Адрес на компьютере | Доступ по умолчанию |
|---|---|---|
| UI, события и логи | http://localhost:8000 | Локальный доступ |
| Superset | http://localhost:8088 | admin / admin |
| JupyterLab | http://localhost:8888 | Токен mmorpg |
| ClickHouse | http://localhost:8123/play | default / clickhouse, база analytics |
| Управление генератором | http://localhost:9100/rate | GET возвращает фазу, POST принимает JSON с batch_size |

Внутри сети Compose сервер БД доступен под именем `clickhouse`. Тома сохраняют данные ClickHouse и настройки Superset между `docker compose down` и `docker compose up -d`. Ноутбуки сохраняются в каталоге `notebooks`. UI читает логи через сокет Docker, доступ к веб-сервисам опубликован на loopback.

## Данные

`dim_players` содержит 120 игроков с классом, фракцией, гильдией и сервером. Строка `fact_combat_events` описывает результат одной активности персонажа. Урон и лечение измеряются за событие. Для крафта роль и сложность пусты. Материализованное представление `hourly_realm_activity` считает события и аномалии по часу UTC и игровому серверу.

При первом старте генератор заполняет последние `BACKFILL_DAYS` дней. Затем каждые `INTERVAL_SECONDS` секунд записывает до `BATCH_SIZE` событий с вечерним пиком. На одном сервере периодически растёт пинг, в части боёв возникает выброс урона. Оба сценария отмечены `is_anomaly`. После перезапуска генератор читает последний timestamp. Размер батча можно менять из UI.

## Проверка записи

В SQL Lab (соединение ClickHouse) или ClickHouse Play выполните запрос несколько раз с интервалом 5 секунд:

```sql
SELECT count() AS events, uniqExact(player_id) AS players,
       max(timestamp) AS latest, countIf(is_anomaly) AS anomalies
FROM analytics.fact_combat_events;
```

Почасовая разбивка по серверам:

```sql
SELECT hour, server_realm, sum(events), sum(anomalies)
FROM analytics.hourly_realm_activity
GROUP BY hour, server_realm ORDER BY hour DESC, server_realm LIMIT 12;
```

При локальной проверке 26 ноября 2026 года до пересоздания контейнеров в базе было 15 863 события, после запуска — 16 543. Время самой ранней записи сохранилось, все 16 543 идентификатора событий были уникальны, в справочнике осталось 120 игроков. На завершённых часах исходные строки и сумма витрины совпали (13 088). Из контейнера Jupyter получен результат 16 623, а через сохранённое подключение Superset позднее — 17 383 события.
