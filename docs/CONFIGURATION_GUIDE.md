# Руководство по конфигурации BOT_AI_V3

## Обзор системы конфигурации

BOT_AI_V3 использует иерархическую систему конфигурации с поддержкой:

- Системных настроек
- Конфигураций трейдеров
- Стратегий
- Переменных окружения

## Структура конфигурационных файлов

```
config/
├── system.yaml           # Основная системная конфигурация
├── traders/             # Конфигурации отдельных трейдеров
│   └── *.yaml
├── strategies/          # Конфигурации стратегий
│   └── *.yaml
├── ml/                  # ML-специфичные конфигурации
│   └── ml_config.yaml
└── logging.yaml         # Настройки логирования
```

## Загрузка конфигурации

### 1. Процесс загрузки (main.py)

```python
# main.py загружает конфигурацию через ConfigManager
config_manager = ConfigManager()
orchestrator = SystemOrchestrator(config_manager)
await orchestrator.initialize()
```

### 2. ConfigManager

ConfigManager ищет конфигурации в следующем порядке:

1. Путь, переданный в конструктор
2. `config/system.yaml` (основной)
3. `/root/trading/config.yaml` (сервер)
4. Текущая директория

### 3. Загрузка трейдеров

Трейдеры загружаются из двух источников:

- Раздел `traders` в `system.yaml`
- Отдельные файлы в `config/traders/*.yaml`

## Добавление нового ML трейдера

### Способ 1: Через отдельный файл конфигурации

1. Создайте файл в `config/traders/my_ml_trader.yaml`:

```yaml
# Уникальный идентификатор трейдера
id: "ml_trader_01"
name: "My ML Trader"
enabled: true

# Биржа и торговая пара
exchange: "bybit"
symbol: "BTC/USDT"

# Стратегия
strategy: "PatchTSTStrategy"

# Параметры стратегии
strategy_config:
  models:
    model_path: "models/saved/best_model.pth"
    scaler_path: "models/saved/scaler.pkl"

  trading:
    min_confidence: 0.65
    position_sizing_mode: "kelly"

# Risk management
risk_management:
  max_risk_per_trade: 0.02
  max_positions: 2
```

2. Система автоматически загрузит трейдера при запуске.

### Способ 2: Через system.yaml

Добавьте трейдера в раздел `traders`:

```yaml
traders:
  - id: "ml_trader_02"
    name: "ML Scalper"
    enabled: true
    exchange: "binance"
    symbol: "ETH/USDT"
    strategy: "PatchTSTStrategy"
    config_file: "config/traders/ml_scalper.yaml"  # Опционально
```

### Способ 3: Программно через API

```python
# Через REST API
POST /api/traders
{
  "id": "ml_trader_03",
  "name": "Dynamic ML Trader",
  "exchange": "okx",
  "symbol": "SOL/USDT",
  "strategy": "PatchTSTStrategy",
  "enabled": true
}
```

## Структура конфигурации трейдера

### Обязательные поля

```yaml
id: "unique_trader_id"      # Уникальный идентификатор
enabled: true               # Включен/выключен
exchange: "bybit"           # Биржа: bybit, binance, okx, etc.
symbol: "BTC/USDT"          # Торговая пара
strategy: "StrategyClass"   # Имя класса стратегии
```

### Настройки торговли (Hedge Mode)

Для фьючерсной торговли с hedge mode добавьте в `system.yaml`:

```yaml
# Настройки торговли
trading:
  hedge_mode: true          # Включить hedge mode (позволяет держать long и short одновременно)
  category: linear          # Тип торговли: linear для USDT фьючерсов
  leverage: 5               # Плечо по умолчанию (1-100)
  max_positions_per_direction: 1  # Максимум позиций на направление

# Position Index в hedge mode:
# - 0: One-way mode (нельзя держать long и short одновременно)
# - 1: Buy/Long позиции в hedge mode
# - 2: Sell/Short позиции в hedge mode
```

### Опциональные поля

```yaml
name: "Display Name"        # Отображаемое имя
description: "Description"  # Описание

# Конфигурация стратегии
strategy_config:
  # Зависит от стратегии

# Risk management
risk_management:
  max_risk_per_trade: 0.02
  max_positions: 3
  stop_loss:
    enabled: true
    type: "dynamic"
    value: 0.02

# Торговые лимиты
trading_limits:
  initial_balance: 10000
  min_balance: 8000
  max_drawdown: 0.20

# Временные ограничения
time_restrictions:
  trading_hours:
    start: "00:00"
    end: "23:59"
  trading_days: [1, 2, 3, 4, 5]

# Параметры исполнения
execution:
  order_type: "limit"
  limit_price_offset: 0.0001
  order_timeout: 30

# Мониторинг
monitoring:
  log_level: "INFO"
  notifications:
    telegram: true
```

## ML-специфичные настройки

Для ML стратегий доступны дополнительные параметры:

```yaml
ml_specific:
  # Пути к моделям
  models:
    model_path: "models/patchtst/model.pth"
    scaler_path: "models/patchtst/scaler.pkl"

  # Параметры inference
  inference:
    batch_size: 32
    use_gpu: true
    cache_predictions: true

  # Обновление модели
  model_update:
    enabled: false
    check_interval_hours: 24

  # Валидация
  prediction_validation:
    enabled: true
    outlier_detection: true
```

## Переменные окружения

Создайте `.env` файл на основе `.env.example`:

```bash
# База данных
PGUSER=obertruper
PGPASSWORD=your_password
PGDATABASE=bot_trading_v3
PGHOST=127.0.0.1
PGPORT=5555

# API ключи бирж
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret

# Claude Code
ANTHROPIC_API_KEY=your_key

# Уведомления
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Валидация конфигурации

Система автоматически валидирует конфигурации при загрузке:

```python
# ConfigManager.validate_config() проверяет:
- Наличие обязательных полей
- Корректность типов данных
- Существование стратегий
- Лимиты и ограничения
```

## Горячая перезагрузка

Конфигурации можно перезагрузить без перезапуска:

```python
# Через API
POST /api/system/reload-config

# Программно
await config_manager.reload_config()
```

## Примеры конфигураций

### 1. Консервативный ML трейдер

```yaml
id: "conservative_ml"
enabled: true
exchange: "bybit"
symbol: "BTC/USDT"
strategy: "PatchTSTStrategy"

strategy_config:
  trading:
    min_confidence: 0.75      # Высокая уверенность
    min_profit_probability: 0.80
    position_sizing_mode: "fixed"
    fixed_risk_pct: 0.01      # 1% риск

risk_management:
  max_positions: 1
  max_portfolio_risk: 0.03    # 3% общий риск
```

### 2. Агрессивный скальпер

```yaml
id: "aggressive_scalper"
enabled: true
exchange: "binance"
symbol: "ETH/USDT"
strategy: "ScalpingStrategy"

strategy_config:
  timeframe: "1m"
  signals_threshold: 0.55

risk_management:
  max_positions: 5
  max_risk_per_trade: 0.03

execution:
  order_type: "market"        # Быстрое исполнение
```

### 3. Арбитражный трейдер

```yaml
id: "arbitrage_bot"
enabled: true
exchanges: ["binance", "bybit"]
symbols: ["BTC/USDT"]
strategy: "ArbitrageStrategy"

strategy_config:
  min_spread: 0.001           # 0.1% минимальный спред
  max_latency_ms: 100
```

## Отладка конфигурации

### 1. Проверка загруженной конфигурации

```python
# Скрипт для проверки
python scripts/check_config.py

# Через API
GET /api/system/config
```

### 2. Логи загрузки

```bash
# Смотрите логи при запуске
tail -f data/logs/system.log | grep -i config
```

### 3. Валидация перед запуском

```python
# Валидация конфигурации
python -m core.config.validator config/traders/my_trader.yaml
```

## Лучшие практики

1. **Используйте отдельные файлы** для сложных трейдеров
2. **Версионируйте конфигурации** в git
3. **Тестируйте на paper trading** перед реальной торговлей
4. **Документируйте изменения** в конфигурациях
5. **Используйте переменные окружения** для секретов
6. **Валидируйте** перед деплоем

## Частые проблемы

### 1. Трейдер не загружается

- Проверьте `enabled: true`
- Проверьте уникальность `id`
- Проверьте наличие стратегии
- Смотрите логи: `grep "trader_id" logs/system.log`

### 2. Ошибка "Strategy not found"

- Проверьте имя класса стратегии
- Убедитесь, что стратегия зарегистрирована
- Проверьте импорты в `strategies/__init__.py`

### 3. Конфигурация не применяется

- Проверьте приоритет загрузки
- Перезагрузите конфигурацию
- Проверьте синтаксис YAML

### 4. Ошибка "position idx not match position mode"

Эта ошибка возникает когда настройки hedge mode не совпадают между биржей и конфигурацией:

- Проверьте настройку `hedge_mode` в `system.yaml`
- Убедитесь что на бирже включен соответствующий режим позиций
- Для Bybit: hedge mode требует position_idx=1 для buy, position_idx=2 для sell
- Если используете one-way mode, установите `hedge_mode: false`

```yaml
# Пример правильной настройки для hedge mode
trading:
  hedge_mode: true
  category: linear
  leverage: 5
```

## Заключение

Система конфигурации BOT_AI_V3 предоставляет гибкий способ управления трейдерами и стратегиями. Используйте это руководство для правильной настройки и избежания распространенных ошибок.
