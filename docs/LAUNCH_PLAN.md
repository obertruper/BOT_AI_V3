# 🚀 Детальный план запуска BOT_AI_V3 - От нуля до автоматической торговли

## 📋 Обзор системы

BOT_AI_V3 - это мульти-трейдерная платформа с поддержкой 7 бирж, ML моделью UnifiedPatchTST (240 входов, 20 выходов), веб-панелью управления и полной автоматизацией торговли.

### Ключевые компоненты

- **Торговый движок**: `main.py` - координация через SystemOrchestrator
- **Веб-панель**: FastAPI на порту 8080 с REST API и WebSocket
- **ML стратегия**: PatchTST модель для предсказания сигналов
- **База данных**: PostgreSQL на порту 5555
- **Поддержка бирж**: Bybit, Binance, OKX, Bitget, Gate.io, KuCoin, Huobi

---

## 🛠️ ЭТАП 1: Подготовка окружения

### 1.1. Проверка системных требований

```bash
# Проверка Python версии (требуется 3.8+)
python3 --version
# Проверка PostgreSQL (должен быть на порту 5555)
sudo systemctl status postgresql
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT version();"

# Проверка Node.js для MCP серверов
node --version  # Требуется 16+
npm --version
```

### 1.2. Настройка виртуального окружения

```bash
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3

# Создание и активация venv
python3 -m venv venv
source venv/bin/activate

# Обновление pip
pip install --upgrade pip setuptools wheel
```

### 1.3. Установка зависимостей

```bash
# Python зависимости
pip install -r requirements.txt

# Дополнительные компоненты
pip install -e ".[monitoring]"  # Prometheus, Grafana
pip install -e ".[telegram]"    # Telegram уведомления
pip install -e ".[dev]"         # Инструменты разработки

# Node.js зависимости для MCP
npm install
```

---

## 🔧 ЭТАП 2: Конфигурация системы

### 2.1. Настройка переменных окружения

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование .env
nano .env
```

**Критически важные настройки в .env:**

```env
# PostgreSQL (ВАЖНО: порт 5555!)
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=ваш_пароль
PGDATABASE=bot_trading_v3

# API ключи бирж (минимум одна биржа, например Bybit)
BYBIT_API_KEY=ваш_api_key
BYBIT_API_SECRET=ваш_api_secret
BYBIT_TESTNET=false  # true для тестовой сети

# Система
LOG_LEVEL=INFO
ENVIRONMENT=production
SECRET_KEY=сгенерировать_случайный_ключ
TIMEZONE=UTC

# Торговые настройки
DEFAULT_LEVERAGE=1
MAX_POSITION_SIZE=1000
RISK_LIMIT_PERCENTAGE=2
```

### 2.2. Проверка и миграция базы данных

```bash
# Проверка подключения к БД
python3 scripts/test_local_db.py

# Применение миграций Alembic
alembic upgrade head

# Визуализация структуры БД (опционально)
python3 scripts/visualize_db.py
```

### 2.3. Подготовка ML модели

```bash
# Создание директории для моделей
mkdir -p models/saved

# Проверка наличия файлов модели
ls -la models/saved/
# Должны быть файлы:
# - best_model_20250728_215703.pth (45MB)
# - data_scaler.pkl
# - config.pkl

# Если файлов нет, скопировать из LLM TRANSFORM проекта
```

---

## 🚀 ЭТАП 3: Запуск основных компонентов

### 3.1. Запуск торгового движка (основной процесс)

```bash
# В первом терминале
source venv/bin/activate
python3 main.py
```

**Ожидаемый вывод:**

```
🚀 Инициализация BOT_Trading v3.0...
✅ Система успешно инициализирована
🎯 Запуск торговой системы...
🟢 Система запущена и готова к работе
```

### 3.2. Запуск веб-панели управления

```bash
# Во втором терминале
source venv/bin/activate
python3 web/launcher.py --reload --debug
```

**Ожидаемый вывод:**

```
🚀 Запуск BOT_Trading v3.0 Web Interface...
📍 URL: http://0.0.0.0:8080
📖 API Docs: http://0.0.0.0:8080/api/docs
🔧 Режим: DEBUG
```

### 3.3. Проверка здоровья системы

```bash
# В третьем терминале
curl http://localhost:8080/api/health

# Ожидаемый ответ:
# {"status": "healthy", "services": {...}}
```

---

## 👥 ЭТАП 4: Настройка мульти-пользовательской системы

### 4.1. Создание первого пользователя через API

```bash
# Регистрация администратора
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@bot-trading.com",
    "password": "secure_password_123",
    "is_admin": true
  }'

# Получение токена авторизации
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password_123"
  }'
# Сохранить полученный JWT токен
```

### 4.2. Создание торгового аккаунта

```bash
# Используя полученный токен
export JWT_TOKEN="ваш_jwt_токен"

curl -X POST http://localhost:8080/api/traders \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MainTrader",
    "exchange": "bybit",
    "initial_balance": 10000,
    "max_position_size": 1000,
    "risk_limit": 2
  }'
```

---

## 📈 ЭТАП 5: Интеграция с биржей (Bybit)

### 5.1. Проверка подключения к бирже

```bash
# Скрипт проверки API подключения
python3 -c "
from exchanges.bybit_exchange import BybitExchange
import asyncio

async def test():
    exchange = BybitExchange()
    await exchange.initialize()
    balance = await exchange.get_balance()
    print(f'Баланс USDT: {balance.get(\"USDT\", 0)}')

asyncio.run(test())
"
```

### 5.2. Настройка торговых пар через веб-панель

```bash
# Добавление торговой пары
curl -X POST http://localhost:8080/api/exchanges/bybit/symbols \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "min_order_size": 0.001,
    "tick_size": 0.01,
    "leverage": 1
  }'
```

---

## 🤖 ЭТАП 6: Запуск ML стратегии

### 6.1. Проверка ML модели

```bash
# Тест загрузки модели
python3 -c "
import torch
import pickle
from ml.logic.patchtst_model import create_unified_model

# Загрузка конфигурации
with open('models/saved/config.pkl', 'rb') as f:
    config = pickle.load(f)

# Создание и загрузка модели
model = create_unified_model(config)
model.load_state_dict(torch.load('models/saved/best_model_20250728_215703.pth'))
print('✅ Модель успешно загружена')
"
```

### 6.2. Конфигурация ML стратегии

```yaml
# strategies/ml_strategy/patchtst_config.yaml
strategy:
  name: "PatchTST_ML_Prod"
  symbol: "BTCUSDT"
  exchange: "bybit"
  timeframe: "15m"

parameters:
  # Пути к модели
  model_path: "models/saved/best_model_20250728_215703.pth"
  scaler_path: "models/saved/data_scaler.pkl"
  config_path: "models/saved/config.pkl"

  # Торговые параметры
  min_confidence: 0.6          # Минимальная уверенность для сигнала
  min_profit_probability: 0.65  # Минимальная вероятность прибыли
  max_risk_threshold: 0.03      # Максимальный риск 3%

  # Веса таймфреймов для голосования
  timeframe_weights:
    15m: 0.3
    1h: 0.3
    4h: 0.3
    12h: 0.1
```

### 6.3. Запуск ML стратегии в тестовом режиме

```bash
# Dry run для проверки
python3 scripts/run_ml_strategy.py \
  --config strategies/ml_strategy/patchtst_config.yaml \
  --symbol BTCUSDT

# Проверка генерации сигналов в логах
tail -f data/logs/ml_strategy.log
```

### 6.4. Активация ML стратегии через веб-панель

```bash
# Добавление стратегии к трейдеру
curl -X POST http://localhost:8080/api/strategies \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "trader_id": 1,
    "strategy_type": "ml_patchtst",
    "config": {
      "symbol": "BTCUSDT",
      "exchange": "bybit",
      "timeframe": "15m",
      "min_confidence": 0.6
    },
    "is_active": true
  }'
```

---

## ⚡ ЭТАП 7: Настройка автоматической торговли

### 7.1. Конфигурация автоматического исполнения

```python
# config/trading_engine.yaml
execution:
  auto_execute: true          # Автоматическое исполнение сигналов
  max_slippage: 0.1          # Максимальное проскальзывание 0.1%
  order_timeout: 30          # Таймаут ордера 30 секунд
  retry_attempts: 3          # Количество попыток

risk_management:
  max_open_positions: 5      # Максимум открытых позиций
  max_drawdown: 10          # Максимальная просадка 10%
  daily_loss_limit: 5       # Дневной лимит потерь 5%
```

### 7.2. Запуск планировщика для минутных сигналов

```bash
# Активация cron-подобного планировщика
curl -X POST http://localhost:8080/api/scheduler/jobs \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ml_signal_generation",
    "schedule": "*/1 * * * *",  # Каждую минуту
    "task": "generate_ml_signals",
    "params": {
      "strategy_id": 1,
      "symbols": ["BTCUSDT"]
    },
    "is_active": true
  }'
```

### 7.3. Мониторинг автоматической торговли

```bash
# Просмотр активных позиций
curl http://localhost:8080/api/positions \
  -H "Authorization: Bearer $JWT_TOKEN"

# Просмотр последних сигналов
curl http://localhost:8080/api/signals?limit=10 \
  -H "Authorization: Bearer $JWT_TOKEN"

# Просмотр исполненных ордеров
curl http://localhost:8080/api/orders?status=filled \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## 📊 ЭТАП 8: Мониторинг и управление

### 8.1. Веб-интерфейс мониторинга

```
Откройте в браузере:
- Главная панель: http://localhost:8080
- API документация: http://localhost:8080/api/docs
- Метрики Prometheus: http://localhost:9090
- Дашборды Grafana: http://localhost:3000
```

### 8.2. Настройка уведомлений Telegram

```bash
# В .env добавить
TELEGRAM_BOT_TOKEN=ваш_бот_токен
TELEGRAM_CHAT_ID=ваш_chat_id

# Активация уведомлений
curl -X POST http://localhost:8080/api/notifications/telegram \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "events": ["signal_generated", "order_filled", "error"],
    "is_active": true
  }'
```

### 8.3. Просмотр логов в реальном времени

```bash
# Основные логи торговли
tail -f data/logs/trading.log

# Логи ошибок
tail -f data/logs/error.log

# Логи ML стратегии
tail -f data/logs/ml_strategy.log

# Все логи через journalctl (если настроен systemd)
journalctl -u bot-trading -f
```

---

## 🔄 ЭТАП 9: Полный производственный запуск

### 9.1. Создание systemd сервисов

```bash
# Создание сервиса для торгового движка
sudo tee /etc/systemd/system/bot-trading.service << EOF
[Unit]
Description=BOT Trading v3 Engine
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
Environment="PATH=/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/venv/bin"
ExecStart=/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Создание сервиса для веб-панели
sudo tee /etc/systemd/system/bot-trading-web.service << EOF
[Unit]
Description=BOT Trading v3 Web Interface
After=network.target bot-trading.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
Environment="PATH=/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/venv/bin"
ExecStart=/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/venv/bin/gunicorn web.api.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### 9.2. Запуск production сервисов

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable bot-trading
sudo systemctl enable bot-trading-web

# Запуск сервисов
sudo systemctl start bot-trading
sudo systemctl start bot-trading-web

# Проверка статуса
sudo systemctl status bot-trading
sudo systemctl status bot-trading-web
```

### 9.3. Настройка nginx reverse proxy (опционально)

```nginx
# /etc/nginx/sites-available/bot-trading
server {
    listen 80;
    server_name bot-trading.local;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## ✅ ЭТАП 10: Проверка полной автоматизации

### 10.1. Контрольный чек-лист

```bash
# 1. Проверка всех сервисов
curl http://localhost:8080/api/health/detailed

# 2. Проверка генерации сигналов (должны появляться каждую минуту)
watch -n 10 'curl -s http://localhost:8080/api/signals/latest | jq'

# 3. Проверка автоматического исполнения
curl http://localhost:8080/api/orders/recent | jq '.[] | {symbol, side, status, created_at}'

# 4. Проверка ML предсказаний
tail -f data/logs/ml_predictions.log | grep "confidence"

# 5. Проверка баланса и P&L
curl http://localhost:8080/api/traders/1/performance | jq
```

### 10.2. Мониторинг ключевых метрик

```
- Количество сигналов в минуту: >0
- Процент успешных ордеров: >95%
- Задержка исполнения: <100ms
- Использование CPU: <50%
- Использование памяти: <2GB
- Точность ML модели: ~63%
```

### 10.3. Команды управления

```bash
# Остановка торговли
curl -X POST http://localhost:8080/api/trading/stop \
  -H "Authorization: Bearer $JWT_TOKEN"

# Возобновление торговли
curl -X POST http://localhost:8080/api/trading/start \
  -H "Authorization: Bearer $JWT_TOKEN"

# Экстренная остановка всех позиций
curl -X POST http://localhost:8080/api/emergency/close-all \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## 🚨 Устранение проблем

### Проблема: "Database connection failed"

```bash
# Проверка PostgreSQL
sudo systemctl status postgresql
psql -p 5555 -U obertruper -d bot_trading_v3

# Проверка прав доступа
sudo -u postgres psql -p 5555 -c "\\du"
```

### Проблема: "Model not found"

```bash
# Проверка файлов модели
ls -la models/saved/
# Если файлов нет, скопировать из резервной копии или LLM TRANSFORM
```

### Проблема: "WebSocket disconnected"

```bash
# Проверка сетевых соединений
netstat -tlnp | grep 8080
# Перезапуск веб-сервиса
sudo systemctl restart bot-trading-web
```

### Проблема: "No signals generated"

```bash
# Проверка данных для ML
python3 -c "
from database.connections import get_db
from database.models import HistoricalData
with get_db() as db:
    count = db.query(HistoricalData).count()
    print(f'Записей в БД: {count}')
"
# Если данных мало, загрузить исторические данные
```

---

## 🎯 Результат успешного запуска

После выполнения всех этапов у вас будет:

1. ✅ **Работающий торговый движок** с SystemOrchestrator
2. ✅ **Веб-панель управления** на <http://localhost:8080>
3. ✅ **ML стратегия**, генерирующая сигналы каждую минуту
4. ✅ **Автоматическое исполнение** ордеров на бирже
5. ✅ **Мульти-пользовательская система** с изоляцией трейдеров
6. ✅ **Мониторинг и алерты** через Telegram
7. ✅ **Production-ready сервисы** с автозапуском

**Система готова к полностью автоматической торговле!** 🚀
