# 🚀 БЫСТРЫЕ ТЕСТЫ СИСТЕМЫ BOT_AI_V3

## 📋 Основные скрипты для проверки системы

### 1. 🔍 Проверка статуса и позиций

```bash
# Проверить открытые позиции
python3 check_positions.py

# Проверить статус системы
python3 unified_launcher.py --status

# Логи в реальном времени
tail -f data/logs/bot_trading_*.log
```

### 2. 📊 Генерация торговых сигналов

```bash
# LONG сигнал для любой криптовалюты
./signal_long.sh BTCUSDT bybit

# SHORT сигнал для любой криптовалюты
./signal_short.sh ETHUSDT bybit

# Мониторинг сигналов
./monitor_signals.sh
```

### 3. ⚡ Быстрое создание позиций

```bash
# Простой LONG ордер ($10)
python3 test_simple_order.py

# SHORT ордер для ETH
python3 quick_eth_order.py

# Прямое создание ордеров из сигналов БД
python3 direct_order_creation.py
```

### 4. 🏃‍♂️ Запуск системы

```bash
# Полный запуск с детальными логами
./start_with_logs.sh

# Только торговое ядро
python3 unified_launcher.py --mode=core

# С ML компонентами
python3 unified_launcher.py --mode=ml

# Остановить всё
./stop_all.sh
```

### 5. 🛠️ Отладка и диагностика

```bash
# Проверка базы данных
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT COUNT(*) FROM orders;"

# Принудительный LONG сигнал через систему
python3 tests/scripts/force_long_signal.py

# Проверка качества кода
black . && ruff check --fix . && mypy .

# Тесты
pytest tests/unit/ -v
```

## 🎯 Быстрая проверка "всё работает"

### Тест 1: Создание позиции (30 сек)

```bash
source venv/bin/activate
python3 test_simple_order.py
python3 check_positions.py
```

### Тест 2: Генерация сигнала (1 мин)

```bash
./signal_long.sh SOLUSDT
python3 direct_order_creation.py
python3 check_positions.py
```

### Тест 3: Полный цикл (3 мин)

```bash
./start_with_logs.sh &
sleep 60
./signal_long.sh BTCUSDT
./signal_short.sh ETHUSDT
python3 direct_order_creation.py
python3 check_positions.py
./stop_all.sh
```

## 📂 Структура тестовых файлов

```
BOT_AI_V3/
├── check_positions.py         # Проверка открытых позиций
├── test_simple_order.py       # Простой тест ордера
├── quick_eth_order.py         # Быстрый SHORT для ETH
├── direct_order_creation.py   # Создание ордеров из сигналов БД
├── signal_long.sh            # Генерация LONG сигналов
├── signal_short.sh           # Генерация SHORT сигналов
├── monitor_signals.sh        # Мониторинг сигналов
├── start_with_logs.sh        # Запуск с логами
├── stop_all.sh              # Остановка всех процессов
└── tests/scripts/
    ├── generate_test_signal.py      # Базовый генератор сигналов
    └── force_long_signal.py         # Принудительный LONG
```

## 🚨 Проверка после изменений

1. **После изменения торговой логики**:

   ```bash
   python3 test_simple_order.py
   python3 check_positions.py
   ```

2. **После обновления ML модели**:

   ```bash
   python3 unified_launcher.py --mode=ml
   tail -f data/logs/bot_trading_*.log | grep "returns_15m"
   ```

3. **После изменения API ключей**:

   ```bash
   python3 -c "from exchanges.bybit.bybit_exchange import BybitExchange; import asyncio; asyncio.run(BybitExchange('key','secret').initialize())"
   ```

## 🔧 Быстрые фиксы

```bash
# Исправить права на скрипты
chmod +x *.sh

# Переустановить зависимости
pip install -r requirements.txt

# Сброс БД (ОСТОРОЖНО!)
alembic downgrade base && alembic upgrade head

# Очистка логов
rm -f data/logs/*.log
```

## 📊 Мониторинг в реальном времени

```bash
# Торговые сигналы
tail -f data/logs/bot_trading_*.log | grep -E "(LONG|SHORT|BUY|SELL)"

# Ошибки
tail -f data/logs/bot_trading_*.log | grep ERROR

# PnL изменения
watch -n 5 "python3 check_positions.py"

# Активность системы
htop -p $(pgrep -f "python.*unified_launcher")
```

---

💡 **Совет**: Сохраните этот файл в закладки - он содержит все команды для быстрой проверки системы!

🎯 **Основной тест**: `python3 test_simple_order.py && python3 check_positions.py`
