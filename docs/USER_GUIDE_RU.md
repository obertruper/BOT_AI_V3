# 📖 Руководство пользователя BOT_AI_V3

## 🚀 Быстрый старт

### Минимальные требования

- Ubuntu 20.04+ / macOS 12+ / Windows 10+ с WSL2
- Python 3.8+
- PostgreSQL 15+
- 8GB RAM минимум (16GB рекомендуется)
- 50GB свободного места на диске
- Стабильное интернет-соединение

### Установка за 5 минут

```bash
# 1. Клонирование репозитория
git clone https://github.com/your-org/BOT_AI_V3.git
cd BOT_AI_V3

# 2. Установка зависимостей
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Настройка окружения
cp .env.example .env
nano .env  # Добавьте ваши API ключи

# 4. Инициализация БД
alembic upgrade head

# 5. Запуск системы
./start_with_logs.sh
```

---

## 🎮 Управление системой

### Основные команды

#### Запуск полной системы

```bash
# Запуск с логированием
./start_with_logs.sh

# Запуск в фоне
python3 unified_launcher.py --daemon
```

#### Запуск отдельных компонентов

```bash
# Только торговля
python3 unified_launcher.py --mode=core

# Только ML предсказания
python3 unified_launcher.py --mode=ml

# Только API и веб-интерфейс
python3 unified_launcher.py --mode=api
```

#### Проверка статуса

```bash
# Статус всех компонентов
python3 unified_launcher.py --status

# Пример вывода:
✅ ML Manager: Running (PID: 12345)
✅ Trading Engine: Running (PID: 12346)
✅ API Server: Running (PID: 12347)
✅ Database: Connected
⚠️  Redis: Not connected (using local cache)
```

#### Остановка системы

```bash
# Корректная остановка
./stop_all.sh

# Принудительная остановка
pkill -f "python.*unified_launcher"
```

#### Просмотр логов

```bash
# Все логи в реальном времени
tail -f data/logs/bot_trading_$(date +%Y%m%d).log

# Только ошибки
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep ERROR

# ML предсказания
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep "ML prediction"

# Торговые операции
tail -f data/logs/bot_trading_$(date +%Y%m%d).log | grep "ORDER"
```

---

## ⚙️ Конфигурация

### Структура конфигурационных файлов

```
config/
├── trading.yaml       # Торговые параметры
├── system.yaml        # Системные настройки
├── ml/
│   └── ml_config.yaml # ML настройки
└── exchanges/         # Настройки бирж
    ├── bybit.yaml
    ├── binance.yaml
    └── ...
```

### Основные параметры

#### trading.yaml - Торговые настройки

```yaml
trading:
  # Режим торговли
  mode: hedge  # hedge или one-way

  # Параметры рисков
  risk:
    max_position_size: 1000  # Макс размер позиции в USDT
    leverage: 5              # Кредитное плечо
    risk_percentage: 2       # % от баланса на сделку

  # Stop Loss / Take Profit
  sl_tp:
    stop_loss_percentage: 2    # % Stop Loss
    take_profit_percentage: 5  # % Take Profit
    trailing_stop: true        # Скользящий стоп

  # Торговые пары
  symbols:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    # ... добавьте нужные пары
```

#### system.yaml - Системные настройки

```yaml
system:
  # Интервалы обновления
  intervals:
    data_update: 60        # Обновление данных (сек)
    balance_check: 30      # Проверка балансов (сек)
    heartbeat: 30          # Heartbeat интервал (сек)

  # Лимиты
  limits:
    max_orders_per_minute: 10
    max_api_calls_per_second: 10

  # Мониторинг
  monitoring:
    enabled: true
    alert_on_errors: true
    metrics_port: 9090
```

#### .env - Секретные данные

```env
# PostgreSQL
PGHOST=localhost
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3

# API ключи бирж
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_secret
BYBIT_TESTNET=false

BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_secret

# Telegram уведомления (опционально)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 📊 Веб-интерфейс

### Доступ к интерфейсу

- **URL**: <http://localhost:5173>
- **Логин**: admin (по умолчанию)
- **Пароль**: задается при первом входе

### Основные разделы

#### Dashboard - Главная панель

- Общая статистика
- Активные позиции
- График P&L
- Последние сигналы

#### Trading - Торговля

- Управление позициями
- История ордеров
- Ручное создание ордеров
- Настройка стратегий

#### Analytics - Аналитика

- Графики производительности
- Статистика по парам
- ML метрики
- Анализ сигналов

#### Settings - Настройки

- Управление API ключами
- Настройка уведомлений
- Параметры рисков
- Системные настройки

---

## 🤖 ML система

### Проверка работы ML

```bash
# Тест ML предсказаний
python3 test_ml_predictions.py

# Проверка уникальности сигналов
python3 test_ml_uniqueness.py

# Анализ качества предсказаний
python3 analyze_ml_quality.py
```

### Настройка ML параметров

```yaml
# config/ml/ml_config.yaml
ml:
  model:
    name: UnifiedPatchTST
    version: 3.0

  features:
    window_size: 100
    prediction_horizon: 15

  signals:
    min_confidence: 0.7
    deduplication_window: 300  # секунд
```

---

## 🔧 Решение типичных проблем

### Проблема: Система не запускается

**Решение:**

```bash
# 1. Проверьте PostgreSQL
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1"

# 2. Проверьте Python окружение
source venv/bin/activate
python --version  # Должно быть 3.8+

# 3. Проверьте зависимости
pip install -r requirements.txt --upgrade

# 4. Проверьте логи
tail -100 data/logs/bot_trading_$(date +%Y%m%d).log
```

### Проблема: Нет торговых сигналов

**Решение:**

```bash
# 1. Проверьте ML Manager
python3 unified_launcher.py --status | grep "ML Manager"

# 2. Проверьте данные
psql -p 5555 -U obertruper -d bot_trading_v3 \
  -c "SELECT COUNT(*) FROM raw_market_data WHERE timestamp > NOW() - INTERVAL '1 hour'"

# 3. Проверьте конфигурацию
cat config/ml/ml_config.yaml | grep min_confidence

# 4. Тест ML модели
python3 test_ml_predictions.py
```

### Проблема: Ордера не создаются

**Решение:**

```bash
# 1. Проверьте балансы
python3 check_balance_detailed.py

# 2. Проверьте API ключи
python3 test_api_signature.py

# 3. Проверьте rate limits
grep "Rate limit" data/logs/bot_trading_$(date +%Y%m%d).log

# 4. Проверьте Trading Engine
python3 unified_launcher.py --status | grep "Trading Engine"
```

### Проблема: Высокая нагрузка на систему

**Решение:**

```bash
# 1. Проверьте процессы
htop -p $(pgrep -f "python.*unified_launcher")

# 2. Оптимизируйте параметры
# В config/system.yaml уменьшите:
# - Частоту обновлений
# - Количество торговых пар
# - Размер окна для ML

# 3. Очистите старые данные
python3 cleanup_old_data.py --days=30

# 4. Перезапустите с оптимизацией
python3 unified_launcher.py --optimize
```

---

## 📈 Мониторинг производительности

### Метрики системы

```bash
# CPU и память
python3 show_system_metrics.py

# Статистика торговли
python3 show_trading_stats.py

# ML производительность
python3 show_ml_metrics.py
```

### Grafana Dashboard

- **URL**: <http://localhost:3000>
- **Логин**: admin
- **Пароль**: admin

### Prometheus метрики

- **URL**: <http://localhost:9090>
- Доступные метрики:
  - `trading_signals_total` - Общее количество сигналов
  - `orders_created_total` - Созданные ордера
  - `ml_predictions_per_second` - ML предсказаний в секунду
  - `api_requests_total` - API запросы к биржам

---

## 🛡️ Безопасность

### Рекомендации по безопасности

1. **API ключи**
   - Используйте только ключи с ограниченными правами
   - Включите IP whitelist на биржах
   - Регулярно ротируйте ключи

2. **Доступ к системе**
   - Используйте сильные пароли
   - Настройте firewall
   - Включите 2FA где возможно

3. **Резервное копирование**

   ```bash
   # Бэкап БД
   pg_dump -p 5555 bot_trading_v3 > backup_$(date +%Y%m%d).sql

   # Бэкап конфигурации
   tar -czf config_backup_$(date +%Y%m%d).tar.gz config/
   ```

---

## 📞 Поддержка

### Получение помощи

1. **Документация**
   - `/docs/SYSTEM_COMPONENTS_RU.md` - Техническая документация
   - `/docs/API_REFERENCE.md` - API справочник
   - `/docs/FAQ.md` - Часто задаваемые вопросы

2. **Логи и диагностика**

   ```bash
   # Сбор диагностической информации
   python3 collect_diagnostics.py

   # Отправка отчета
   python3 send_support_report.py
   ```

3. **Контакты**
   - Email: <support@botai.tech>
   - Telegram: @botai_support
   - GitHub Issues: <https://github.com/your-org/BOT_AI_V3/issues>

---

## 🎯 Советы по оптимизации

### Для начинающих

1. Начните с малых сумм
2. Используйте только 2-3 торговые пары
3. Установите консервативные stop-loss (3-5%)
4. Мониторьте систему первые дни

### Для опытных пользователей

1. Настройте кастомные стратегии
2. Оптимизируйте ML параметры под ваш стиль
3. Используйте множественные биржи
4. Внедрите собственные индикаторы

### Производительность

1. **Оптимизация БД**

   ```sql
   -- Анализ и оптимизация
   ANALYZE;
   VACUUM FULL;
   ```

2. **Оптимизация ML**
   - Уменьшите window_size для быстрых предсказаний
   - Используйте GPU для ускорения
   - Настройте batch processing

3. **Сетевая оптимизация**
   - Используйте WebSocket где возможно
   - Настройте connection pooling
   - Минимизируйте API запросы

---

## 📅 Регулярное обслуживание

### Ежедневно

- Проверка логов на ошибки
- Мониторинг позиций
- Проверка балансов

### Еженедельно

- Анализ производительности
- Обновление стратегий
- Бэкап данных

### Ежемесячно

- Очистка старых данных
- Оптимизация БД
- Обновление зависимостей
- Ротация API ключей

---

## 🚀 Обновление системы

### Процедура обновления

```bash
# 1. Остановка системы
./stop_all.sh

# 2. Бэкап
pg_dump -p 5555 bot_trading_v3 > backup_before_update.sql
tar -czf config_backup.tar.gz config/

# 3. Получение обновлений
git pull origin main

# 4. Обновление зависимостей
pip install -r requirements.txt --upgrade

# 5. Миграция БД
alembic upgrade head

# 6. Перезапуск
./start_with_logs.sh
```

---

## 📝 Заметки

### Важные файлы

- `unified_launcher.py` - Главная точка входа
- `config/trading.yaml` - Торговые настройки
- `.env` - Секретные данные
- `data/logs/` - Директория с логами

### Горячие клавиши в веб-интерфейсе

- `Ctrl+K` - Быстрый поиск
- `Ctrl+/` - Помощь
- `Ctrl+S` - Сохранить настройки
- `Esc` - Закрыть модальное окно

### Полезные скрипты

```bash
# Быстрая проверка системы
./scripts/health_check.sh

# Анализ прибыльности
python3 analyze_profitability.py

# Экспорт статистики
python3 export_stats.py --format=csv
```

---

*Последнее обновление: Январь 2025*
*Версия: 3.0.0*
