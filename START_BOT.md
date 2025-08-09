# 🚀 Инструкция по запуску BOT_AI_V3

## Быстрый старт

### 1. Активируйте виртуальное окружение

```bash
source venv/bin/activate
```

### 2. Запустите торгового бота

#### Простой бот с SMA стратегией

```bash
python3 start_trading_bot.py
```

#### Полноценная ML система

```bash
python3 unified_launcher.py --mode=ml
```

### 3. Мониторинг в реальном времени

В отдельном терминале:

```bash
# Общий мониторинг
./monitor_realtime.sh simple

# ML сигналы
./monitor_ml_realtime.sh
```

## 📊 Текущий статус

✅ **Работает:**

- Подключение к Bybit
- GPU RTX 5090 для ML
- Генерация торговых сигналов
- SMA стратегия

⚠️ **В разработке:**

- ML генерирует только NEUTRAL сигналы
- Нужна настройка порогов в config/ml/ml_config.yaml

## 🛑 Остановка бота

```bash
# Ctrl+C в терминале с ботом
# или
pkill -f "python.*start_trading_bot"
```

## 📈 Проверка логов

```bash
# Последние сигналы
tail -f data/logs/bot_trading_*.log | grep "СИГНАЛ"

# Ошибки
tail -f data/logs/bot_trading_*.log | grep "ERROR"
```
