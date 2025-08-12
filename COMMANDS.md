# 📋 КОМАНДЫ УПРАВЛЕНИЯ BOT_AI_V3

## ✅ Текущий статус системы: ЗАПУЩЕНА

### Проверка статуса

```bash
./check_status.sh
```

## 🚀 Запуск системы

### Запуск с мониторингом логов (рекомендуется)

```bash
./start_with_logs.sh
```

Это запустит систему и покажет логи в реальном времени.

### Альтернативные способы запуска

```bash
# Основной запуск
python unified_launcher.py

# Только торговля
python unified_launcher.py --mode=core

# С машинным обучением
python unified_launcher.py --mode=ml
```

## 📊 Мониторинг в реальном времени

### Все логи

```bash
tail -f data/logs/bot_trading_*.log
```

### Только важные события

```bash
tail -f data/logs/bot_trading_*.log | grep -E "signal|order|position|SL|TP|leverage"
```

### Мониторинг SL/TP

```bash
./monitor_sltp.sh
```

### Мониторинг сигналов

```bash
./monitor_signals.sh
```

### Только ошибки

```bash
tail -f data/logs/bot_trading_*.log | grep ERROR
```

## 📡 Генерация тестовых сигналов

### LONG сигнал

```bash
# Для DOGEUSDT
./signal_long.sh DOGEUSDT

# Для BTCUSDT
./signal_long.sh BTCUSDT

# По умолчанию SOLUSDT
./signal_long.sh
```

### SHORT сигнал

```bash
# Для ETHUSDT
./signal_short.sh ETHUSDT

# По умолчанию SOLUSDT
./signal_short.sh
```

### Прямой вызов Python скриптов

```bash
# LONG сигнал
python tests/scripts/force_long_signal.py

# Тестовый сигнал
python tests/scripts/generate_test_long_signal.py
```

## 🛑 Остановка системы

### Полная остановка

```bash
./stop_all.sh
```

### Проверка что все остановлено

```bash
ps aux | grep python | grep -E "unified|trading|bot"
```

## 🔍 Проверка позиций и баланса

### Все позиции с плечом

```bash
python utils/checks/check_all_positions.py
```

### Баланс

```bash
python utils/checks/check_balance.py
```

### Позиции и ордера

```bash
python utils/checks/check_positions_and_orders.py
```

### Проверка конкретной позиции (DOGE)

```bash
python utils/checks/check_doge_position.py
```

## 🧪 Тестирование

### Тест торговли с SL/TP

```bash
python tests/integration/test_real_trading.py
```

### Полный тест системы

```bash
python tests/integration/test_complete_trading.py
```

## 📈 Текущие настройки

| Параметр | Значение | Файл |
|----------|----------|------|
| Плечо | 5x | config/trading.yaml |
| Риск на сделку | 2% | config/trading.yaml |
| Фиксированный баланс | $500 | config/trading.yaml |
| Stop Loss | -2% | config/trading.yaml |
| Take Profit | +3% | config/trading.yaml |
| Минимальный ордер | $5 | Bybit requirement |

## 🔧 Быстрые фиксы

### Исправить плечо для всех позиций

```bash
python utils/checks/check_all_positions.py
# Скрипт автоматически установит 5x
```

### Проверить API ключи

```bash
python utils/checks/check_api_keys.py
```

## 📁 Структура файлов

| Каталог | Содержание |
|---------|------------|
| tests/integration/ | Интеграционные тесты |
| tests/scripts/ | Тестовые скрипты и генераторы |
| utils/checks/ | Проверочные утилиты |
| utils/fixes/ | Скрипты исправлений |
| docs/solutions/ | Документация решений |
| data/logs/ | Все логи системы |

## ⚡ Горячие клавиши в логах

При просмотре логов через `tail -f`:

- `Ctrl+C` - выйти из просмотра (система продолжит работать)
- `Ctrl+S` - приостановить вывод
- `Ctrl+Q` - возобновить вывод

## 🆘 Решение проблем

### Система не запускается

```bash
# Проверить что нет запущенных процессов
./stop_all.sh

# Проверить виртуальное окружение
source venv/bin/activate

# Проверить .env файл
cat .env | grep BYBIT
```

### Сигналы не генерируются

```bash
# Проверить что система запущена
./check_status.sh

# Проверить логи на ошибки
tail -100 data/logs/bot_trading_*.log | grep ERROR
```

### SL/TP не устанавливаются

```bash
# Проверить позиции
python utils/checks/check_all_positions.py

# Проверить режим позиций (должен быть Hedge Mode)
python utils/checks/check_position_mode.py
```

---

**Последнее обновление**: 10.08.2025
**Версия**: 3.0.0
**Статус системы**: ✅ РАБОТАЕТ
