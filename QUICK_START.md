# 🚀 BOT Trading v3 - Быстрый старт

## 📋 Требования

- Python 3.8+
- PostgreSQL 16 (на порту 5555)
- Redis (опционально)
- 8GB+ RAM
- Unix-подобная ОС (Linux/macOS)

## 🔧 Установка за 5 минут

### 1. Клонирование и подготовка

```bash
# Переход в директорию проекта
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование .env файла
nano .env
```

**Минимальные настройки в .env:**

```env
# PostgreSQL (порт 5555!)
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3

# Хотя бы одна биржа (например, Bybit)
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret

# Секретный ключ
SECRET_KEY=your_secret_key_here
```

### 3. Подготовка базы данных

```bash
# Создание БД (если еще не создана)
sudo -u postgres psql -p 5555 -c "CREATE DATABASE bot_trading_v3 OWNER obertruper;"

# Применение миграций
alembic upgrade head
```

### 4. Проверка готовности

```bash
# Автоматическая проверка всех компонентов
python scripts/check_v3_readiness.py
```

## 🎯 Запуск системы

### Вариант 1: Автоматический запуск (рекомендуется)

```bash
# Запуск через скрипт с проверками
./scripts/start_v3.sh
```

### Вариант 2: Ручной запуск

```bash
# Основной торговый движок
python main.py

# В отдельном терминале - веб-интерфейс
python web/launcher.py
```

### Вариант 3: Production запуск

```bash
# С помощью systemd
sudo systemctl start bot-trading-v3

# Или через Docker
docker-compose up -d
```

## 📊 Доступ к системе

После успешного запуска:

- **Веб-интерфейс**: <http://localhost:8080>
- **API документация**: <http://localhost:8080/api/docs>
- **Prometheus метрики**: <http://localhost:9090>
- **Grafana дашборды**: <http://localhost:3000>

## 🔍 Проверка работы

### 1. Проверка статуса через API

```bash
curl http://localhost:8080/api/health
```

### 2. Проверка логов

```bash
# Основные логи
tail -f logs/trading.log

# Ошибки
tail -f logs/error.log
```

### 3. Проверка через Telegram бота

Если настроен Telegram бот:

- Отправьте `/status` для проверки статуса
- Отправьте `/help` для списка команд

## 🛠️ Первые шаги после запуска

### 1. Создание первого трейдера

```bash
# Через скрипт
python scripts/create_ml_trader.py --name ml_trader_1 --symbol BTCUSDT

# Или через веб-интерфейс
# Перейдите на http://localhost:8080/traders/create
```

### 2. Запуск ML стратегии

```bash
# Тестовый запуск
python scripts/demo_ml_trader.py

# Боевой режим
python scripts/run_ml_strategy.py --symbol BTCUSDT --live
```

### 3. Мониторинг производительности

```bash
# Системный мониторинг
python scripts/monitor_system.py

# Анализ логов
python scripts/analyze_logs.py --period 1h
```

## ⚠️ Важные моменты

1. **PostgreSQL на порту 5555** - не стандартный 5432!
2. **Не указывайте PGHOST** для локального подключения
3. **ML модель** должна быть в `models/saved/best_model_*.pth`
4. **API ключи** должны иметь права на торговлю
5. **Проверяйте логи** при первом запуске

## 🆘 Решение проблем

### База данных не подключается

```bash
# Проверка PostgreSQL
systemctl status postgresql

# Проверка порта
sudo netstat -tulpn | grep 5555

# Тест подключения
psql -p 5555 -U obertruper -d bot_trading_v3 -c '\l'
```

### ML модель не загружается

```bash
# Проверка модели
python scripts/check_ml_model.py

# Подготовка конфигурации
python scripts/prepare_model_config.py
```

### Недостаточно памяти

```bash
# Оптимизация памяти
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
python main.py
```

## 📚 Дополнительная документация

- [Полная документация](docs/README.md)
- [Настройка ML трейдера](docs/ML_TRADER_SETUP.md)
- [Конфигурация системы](docs/CONFIGURATION_GUIDE.md)
- [API референс](docs/API_REFERENCE.md)

## 💡 Полезные команды

```bash
# Остановка системы
pkill -f "python main.py"

# Очистка логов
rm -rf logs/*.log

# Бэкап конфигурации
cp -r config/ config_backup_$(date +%Y%m%d)

# Обновление зависимостей
pip install -r requirements.txt --upgrade
```

---

**Версия**: 3.0.0-alpha | **Обновлено**: 30 июля 2025
