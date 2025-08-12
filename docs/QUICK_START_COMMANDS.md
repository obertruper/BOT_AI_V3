# 🚀 Быстрые команды для BOT_AI_V3

## ✅ Да, все эти команды работают

Все скрипты созданы и готовы к использованию. Вот подробное описание:

## 📋 Доступные команды

### 1. 🟢 Запуск системы с мониторингом

```bash
./start_with_logs.sh
```

**Что делает:**

- Проверяет PostgreSQL на порту 5555
- Активирует виртуальное окружение
- Запускает unified_launcher.py с ML режимом
- Открывает 4 окна мониторинга в tmux:
  - Логи launcher
  - Логи торговли
  - Мониторинг сигналов
  - Мониторинг SL/TP

### 2. 📊 Генерация тестовых сигналов

#### Интерактивный режим

```bash
./generate_signal.sh
```

**Возможности:**

- Выбор типа сигнала (LONG/SHORT)
- Выбор из 10 популярных криптовалют
- Настройка размера позиции
- Настройка SL/TP процентов
- Добавление описания

#### Быстрые команды

```bash
# LONG для Solana (по умолчанию)
./signal_long.sh

# SHORT для Solana
./signal_short.sh

# LONG для Bitcoin
./signal_long.sh BTCUSDT

# SHORT для Ethereum
./signal_short.sh ETHUSDT

# С указанием биржи
./signal_long.sh BTCUSDT binance
```

### 3. 📈 Мониторинг

#### Только SL/TP

```bash
./monitor_sltp.sh
```

- Отслеживает установку SL/TP
- Показывает статусы позиций
- Обновляется в реальном времени

#### Только сигналы

```bash
./monitor_signals.sh
```

- Показывает новые сигналы
- Отслеживает обработку сигналов
- Показывает создание ордеров

#### Статус системы

```bash
./check_status.sh
```

- Проверяет запущенные процессы
- Показывает использование ресурсов
- Проверяет последние ошибки
- Статус базы данных

### 4. 🛑 Остановка системы

```bash
./stop_all.sh
```

- Останавливает все процессы BOT_AI_V3
- Закрывает tmux сессии
- Сохраняет логи
- Graceful shutdown

## 💡 Примеры использования

### Полный цикл тестирования

```bash
# 1. Запустить систему
./start_with_logs.sh

# 2. Подождать инициализацию (30 сек)
sleep 30

# 3. Создать тестовый LONG сигнал для SOL
./signal_long.sh

# 4. Проверить обработку (в tmux окнах)
# Или отдельно:
./monitor_signals.sh  # в одном терминале
./monitor_sltp.sh     # в другом терминале

# 5. Проверить статус
./check_status.sh

# 6. Остановить систему
./stop_all.sh
```

### Быстрый тест разных монет

```bash
# Bitcoin LONG
./signal_long.sh BTCUSDT

# Ethereum SHORT
./signal_short.sh ETHUSDT

# Dogecoin LONG
./signal_long.sh DOGEUSDT

# Polygon SHORT
./signal_short.sh MATICUSDT
```

## 🔧 Дополнительные скрипты

### Мониторинг ML в реальном времени

```bash
./monitor_ml_realtime.sh
```

### Просмотр всех логов

```bash
./view_logs.sh
```

### Проверка системы

```bash
./check_system.sh
```

## ⚠️ Требования

1. **PostgreSQL** должен быть запущен на порту 5555
2. **Python venv** должен быть создан и содержать все зависимости
3. **API ключи** должны быть в `.env` файле
4. **tmux** должен быть установлен для мониторинга

## 🐛 Устранение проблем

### Если скрипт не запускается

```bash
# Дать права на выполнение
chmod +x *.sh

# Проверить venv
source venv/bin/activate
pip install -r requirements.txt
```

### Если PostgreSQL недоступен

```bash
# Проверить порт
export PGPORT=5555
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1;"
```

### Если tmux не установлен

```bash
# Ubuntu/Debian
sudo apt-get install tmux

# Или запускать без мониторинга
python3 unified_launcher.py --mode=ml
```

---

**Все команды протестированы и работают! 🎉**
