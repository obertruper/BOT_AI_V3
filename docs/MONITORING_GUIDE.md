# 📊 Руководство по запуску и мониторингу BOT_AI_V3

## 🚀 Быстрый старт

### 1. Запуск с мониторингом логов

```bash
./start_with_logs.sh
```

Запускает систему и показывает важные события в реальном времени с цветовым выделением.

### 2. Обычный запуск

```bash
python3 unified_launcher.py --mode=ml
```

## 🔍 Мониторинг

### Проверка статуса системы

```bash
./check_status.sh
```

Показывает:

- Активные процессы
- Статистику из БД
- Последние ошибки
- Последние SL/TP события

### Мониторинг только SL/TP

```bash
./monitor_sltp.sh
```

Отслеживает:

- Создание SL/TP ордеров
- Обновления трейлинг стопа
- Частичные Take Profit
- Срабатывания SL/TP

### Мониторинг торговых сигналов

```bash
./monitor_signals.sh
```

Отслеживает:

- ML сигналы
- Создание ордеров
- Исполнение ордеров
- Открытие/закрытие позиций

### Просмотр всех логов

```bash
tail -f data/logs/*.log
```

### Фильтрация логов

```bash
# Только ошибки
tail -f data/logs/*.log | grep ERROR

# Только SL/TP
tail -f data/logs/*.log | grep -E "SL|TP|stop|profit"

# Только сигналы
tail -f data/logs/*.log | grep signal

# Только позиции
tail -f data/logs/*.log | grep position
```

## 🎯 Генерация тестовых сигналов

### Интерактивный генератор (рекомендуется)

```bash
./generate_signal.sh
```

Позволяет выбрать тип сигнала, монету и биржу через меню.

### Быстрая генерация LONG сигнала

```bash
./signal_long.sh            # LONG для SOLUSDT
./signal_long.sh BTCUSDT    # LONG для Bitcoin
./signal_long.sh ETHUSDT    # LONG для Ethereum
```

### Быстрая генерация SHORT сигнала

```bash
./signal_short.sh           # SHORT для SOLUSDT
./signal_short.sh BTCUSDT   # SHORT для Bitcoin
./signal_short.sh ETHUSDT   # SHORT для Ethereum
```

### Прямая генерация через Python

```bash
# LONG сигнал для Solana
python3 generate_test_signal.py --type LONG --symbol SOLUSDT --exchange bybit

# SHORT сигнал для Bitcoin
python3 generate_test_signal.py --type SHORT --symbol BTCUSDT --exchange bybit
```

## 🛑 Остановка системы

### Остановить все процессы

```bash
./stop_all.sh
```

### Принудительная остановка

```bash
pkill -9 -f 'python.*BOT_AI_V3'
```

## 📁 Расположение логов

- `data/logs/bot_trading_YYYYMMDD.log` - основной лог торговли
- `data/logs/trading.log` - торговые операции
- `data/logs/launcher.log` - лог запуска
- `data/logs/error.log` - только ошибки

## 🎨 Цветовая схема логов

- 🔴 **Красный** - ошибки (ERROR, CRITICAL)
- 🟡 **Желтый** - предупреждения (WARNING)
- 🔵 **Голубой** - SL/TP события
- 🟣 **Пурпурный** - торговые сигналы
- 🟢 **Зеленый** - успешные операции, позиции

## 💡 Полезные команды

### Проверка последних сигналов в БД

```sql
psql -p 5555 -U obertruper -d bot_trading_v3 -c "
SELECT created_at, symbol, signal_type, strength, suggested_stop_loss, suggested_take_profit
FROM signals
ORDER BY created_at DESC
LIMIT 10;"
```

### Проверка активных позиций

```sql
psql -p 5555 -U obertruper -d bot_trading_v3 -c "
SELECT symbol, side, quantity, entry_price, current_price, unrealized_pnl
FROM positions
WHERE status = 'open';"
```

### Проверка SL/TP ордеров

```sql
psql -p 5555 -U obertruper -d bot_trading_v3 -c "
SELECT o.symbol, o.side, o.order_type, o.price, o.stop_loss, o.take_profit, o.status
FROM orders o
WHERE o.stop_loss IS NOT NULL OR o.take_profit IS NOT NULL
ORDER BY o.created_at DESC
LIMIT 10;"
```

## 🔧 Отладка

### Если система не запускается

1. Проверьте PostgreSQL: `psql -p 5555 -U obertruper -d bot_trading_v3`
2. Проверьте .env файл: `cat .env | grep API_KEY`
3. Проверьте логи: `tail -100 data/logs/launcher.log`

### Если SL/TP не создаются

1. Проверьте конфигурацию: `grep -A 10 "sltp:" config/system.yaml`
2. Проверьте логи: `./monitor_sltp.sh`
3. Проверьте hedge mode на бирже

### Если нет сигналов

1. Проверьте ML систему: `grep "ML" data/logs/*.log | tail -20`
2. Проверьте данные: `python3 scripts/check_data_availability.py`

---

**Совет**: Всегда запускайте через `./start_with_logs.sh` для удобного мониторинга!
