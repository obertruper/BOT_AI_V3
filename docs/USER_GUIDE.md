# BOT_Trading v3.0 — Руководство пользователя

## Быстрый старт

1. Подготовка окружения

```
bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
source venv/bin/activate
export PGPORT=5555
```

2. Запуск системы

```
bash
# Полный режим (ядро + API + ML)
python3 unified_launcher.py --mode=full

# Только ядро
python3 unified_launcher.py --mode=core

# Только ML
python3 unified_launcher.py --mode=ml
```

3. Веб-интерфейс

- API: <http://localhost:8080>
- Swagger: <http://localhost:8080/api/docs>
- Frontend (dev): <http://localhost:5173>

## Логи и мониторинг

- Основные логи: `data/logs/bot_trading_YYYYMMDD.log`
- Ошибки: `data/logs/errors.log`
- Лаунчер: `data/logs/launcher_full.log`

Быстрый просмотр:

```
bash
tail -f data/logs/bot_trading_$(date +%Y%m%d).log
```

## Проверка статуса системы

```
bash
# Health
curl -s http://localhost:8080/api/health | jq .

# Статус системы
curl -s http://localhost:8080/api/system/status | jq .

# Конфигурация (без секретов)
curl -s http://localhost:8080/api/system/config/raw | jq .
```

## Настройки (Settings)

Страница Настроек отображает и позволяет обновлять часть системной конфигурации.

- Получить текущую конфигурацию:

```
bash
curl -s http://localhost:8080/api/system/config/raw | jq .
```

- Обновить конфигурацию:

```
bash
curl -s -X POST http://localhost:8080/api/system/config/update \
  -H 'Content-Type: application/json' \
  -d '{"updates": {"environment": "development", "web_interface": {"host": "0.0.0.0", "port": 8080}}}' | jq .
```

Примечания:

- Секреты (.env, API ключи) не выводятся и не коммитятся
- Обновление сохраняется через `ConfigManager.update_system_config()`

## Трейдеры (Traders)

- Список трейдеров: `GET /api/traders`
- Запуск трейдера: `POST /api/traders/{id}/start`
- Стоп трейдера: `POST /api/traders/{id}/stop`

Фронтенд показывает:

- Капитал, P&L, ROI, число сделок, винрейт, аптайм
- Статус и последнюю активность

Данные берутся из веб-моста (mock при отсутствии оркестратора). Для реальных данных убедитесь, что `SystemOrchestrator` инициализирован и передан в веб.

## Позиции (Positions)

- Список позиций: `GET /api/positions?trader_id=...`
- Обновление SL/TP: `PUT /api/positions/{id}/stop-loss|take-profit` (когда реализовано)
- Частичное закрытие: `POST /api/positions/{id}/close` (когда реализовано)

Фронтенд страница `Positions` агрегирует P&L, общую стоимость и выводит карточки позиций.

## Биржи (Exchanges)

- Список бирж: `GET /api/exchanges`
- Детали биржи: `GET /api/exchanges/{name}`
- Тест подключения: `POST /api/exchanges/{name}/test`

## Отладка

- ImportError: `source venv/bin/activate && pip install -r requirements.txt`
- БД: `psql -p 5555 -U obertruper -d bot_trading_v3`
- ML кэш: проверьте TTL в `ml/ml_signal_processor.py` (5 минут)

## Тесты

```
bash
pytest tests/unit -v --cov
```

## Полезные команды

```
bash
# Генерация тестового сигнала
python3 generate_test_signal.py --type LONG --symbol SOLUSDT --exchange bybit

# Старт с логами
bash start_with_logs.sh
```

## FAQ

- Почему нет данных на страницах?
  - В dev-режиме веб-мост использует mock-данные. Для реальных данных запустите полный режим (`--mode=full`) или интегрируйте оркестратор в веб.
- Почему баланс 0?
  - Проверьте подключение к бирже и `TraderManager` метрики. При mock-режиме баланс тестовый.
