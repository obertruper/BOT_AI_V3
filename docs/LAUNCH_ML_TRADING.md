# 🚀 Запуск ML торговой системы

## 📋 Предварительные требования

1. **PostgreSQL на порту 5555**

```bash
# Проверка статуса
sudo systemctl status postgresql

# Проверка подключения
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT 1;"
```

2. **Настроенный .env файл**

```bash
# Скопируйте и отредактируйте
cp .env.example .env
nano .env

# Обязательные переменные:
# - PGUSER, PGPASSWORD, PGDATABASE
# - BYBIT_API_KEY, BYBIT_API_SECRET (или другая биржа)
```

3. **ML модели**

```bash
# Проверка наличия
ls -la models/saved/
# Должны быть:
# - best_model_20250728_215703.pth
# - data_scaler.pkl
```

## 🎯 Быстрый запуск

### Вариант 1: Автоматический (рекомендуется)

```bash
# Запуск с проверками и вопросами
./start_ml_trading.sh
```

### Вариант 2: Прямой запуск

```bash
# Активация venv
source venv/bin/activate

# Применение миграций
alembic upgrade head

# Запуск
python main.py
```

### Вариант 3: Только ML тестирование

```bash
# Тест real-time генерации сигналов
python scripts/test_realtime_signals.py

# Демо ML трейдера
python scripts/demo_ml_trader.py
```

## 📊 Проверка данных

### Проверка готовности

```bash
python scripts/check_data_availability.py
```

### Загрузка исторических данных

```bash
# Загрузить за 30 дней (по умолчанию)
python scripts/load_historical_data.py

# Загрузить за 7 дней
python scripts/load_historical_data.py --days 7

# Загрузить конкретные символы
python scripts/load_historical_data.py --symbols BTCUSDT ETHUSDT
```

## 🔍 Мониторинг

### Логи в реальном времени

```bash
# Основные логи
tail -f data/logs/trading.log

# ML сигналы
tail -f data/logs/ml_signals.log

# Ошибки
tail -f data/logs/errors.log
```

### Веб-интерфейс

- **Дашборд**: <http://localhost:8080>
- **API документация**: <http://localhost:8080/api/docs>
- **Метрики**: <http://localhost:9090/metrics>

### Проверка сгенерированных сигналов

```bash
# Последние ML сигналы из БД
python -c "
from database.connections import get_db
from database.models import ProcessedMarketData
with get_db() as db:
    signals = db.query(ProcessedMarketData)\\
        .filter(ProcessedMarketData.prediction_meta != None)\\
        .order_by(ProcessedMarketData.created_at.desc())\\
        .limit(10).all()
    for s in signals:
        meta = s.prediction_meta
        print(f'{s.symbol}: {meta.get(\"action\")} '
              f'(confidence: {meta.get(\"confidence\"):.2f}, '
              f'strength: {meta.get(\"signal_strength\"):.2f})')
"
```

## ⚙️ Конфигурация ML

### Основные настройки (config/system.yaml)

```yaml
ml:
  enabled: true  # Включить/выключить ML
  signal_generation:
    interval_seconds: 60  # Частота генерации
  symbols:
    - "BTCUSDT"
    - "ETHUSDT"
    # ... добавьте свои
  filters:
    min_confidence: 0.45  # Минимальная уверенность
    min_signal_strength: 0.3  # Минимальная сила сигнала
```

### Расширенные настройки (config/ml/ml_config.yaml)

- Параметры модели
- Feature engineering
- Обработка данных
- Risk management

## 🛑 Остановка системы

### Graceful shutdown

```bash
# Ctrl+C в терминале с main.py
# или
kill -SIGTERM $(pgrep -f "python main.py")
```

### Экстренная остановка

```bash
# Остановить все процессы
pkill -f "python.*BOT_AI_V3"
```

## 🐛 Решение проблем

### PostgreSQL недоступен

```bash
# Проверить порт
sudo netstat -tlnp | grep 5555

# Проверить конфигурацию
sudo nano /etc/postgresql/*/main/postgresql.conf
# port = 5555
```

### Недостаточно данных

```bash
# Загрузить минимум для тестов
python scripts/load_historical_data.py --symbols BTCUSDT --days 3
```

### ML модель не найдена

```bash
# Скопировать из LLM TRANSFORM
cp "/mnt/SSD/PYCHARMPRODJECT/LLM TRANSFORM/crypto_ai_trading/models/saved/*" models/saved/
```

### Out of Memory при ML

```yaml
# Уменьшить batch_size в config/system.yaml
ml:
  signal_generation:
    batch_size: 5  # Вместо 10
```

## 📈 Оптимизация производительности

1. **Уменьшить количество символов** - начните с 3-5
2. **Увеличить интервал генерации** - 120 секунд вместо 60
3. **Использовать GPU** - device: "cuda" в конфигурации
4. **Включить кеширование** - уже включено по умолчанию

## 🎯 Следующие шаги

1. **Мониторинг сигналов** - следите за качеством предсказаний
2. **Настройка фильтров** - подберите оптимальные пороги
3. **Добавление символов** - постепенно увеличивайте покрытие
4. **Интеграция с трейдерами** - подключите ML сигналы к стратегиям

---

💡 **Совет**: Начните с минимального набора символов (2-3) и постепенно увеличивайте после проверки стабильности системы.
