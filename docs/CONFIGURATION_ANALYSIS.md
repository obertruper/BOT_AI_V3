# Анализ структуры конфигурации BOT_AI_V3

## Резюме анализа

BOT_AI_V3 использует гибкую и масштабируемую систему конфигурации без хардкода. Все настройки загружаются из YAML файлов и переменных окружения.

## Как система загружает конфигурацию

### 1. Точка входа (main.py)

```python
# main.py - строки 48-57
self.config_manager = ConfigManager()
self.orchestrator = SystemOrchestrator(self.config_manager)
await self.orchestrator.initialize()
```

**Процесс:**

1. Создается `ConfigManager` без параметров
2. `ConfigManager` передается в `SystemOrchestrator`
3. При инициализации оркестратор вызывает `initialize()` менеджера конфигурации

### 2. ConfigManager - загрузка конфигураций

**Поиск конфигураций (config_manager.py, строки 59-64):**

```python
self._default_config_paths = [
    "config.yaml",              # Корень проекта
    "config/system.yaml",       # v3.0 система
    "/root/trading/config.yaml", # Сервер
    os.path.join(os.getcwd(), "config.yaml")  # Текущая директория
]
```

**Загрузка трейдеров из двух источников:**

1. **Из отдельных файлов** (строки 139-155):
   - Сканирует `config/traders/*.yaml`
   - Каждый файл = отдельный трейдер
   - ID трейдера = имя файла без расширения

2. **Из system.yaml** (строки 157-162):
   - Читает раздел `traders` в system.yaml
   - Добавляет в общий реестр трейдеров

### 3. SystemOrchestrator - инициализация трейдеров

**Загрузка конфигураций (orchestrator.py, строки 164-173):**

```python
async def _load_trader_configurations(self) -> None:
    trader_ids = self.config_manager.get_all_trader_ids()

    for trader_id in trader_ids:
        if self.config_manager.is_trader_enabled(trader_id):
            # Трейдер готов к запуску
```

**Автоматический запуск (строки 189-191):**

```python
# При старте системы
await self._start_enabled_traders()
```

### 4. TraderManager - создание трейдеров

**Процесс создания (trader_manager.py, строки 252-284):**

```python
async def _start_enabled_traders(self) -> None:
    trader_ids = self.config_manager.get_all_trader_ids()

    for trader_id in trader_ids:
        if self.config_manager.is_trader_enabled(trader_id):
            await self.start_trader(trader_id)

async def create_trader(self, trader_id: str) -> TraderContext:
    # Создание через фабрику
    trader_context = await self.trader_factory.create_trader(trader_id)
```

## Структура конфигурационных файлов

### config/system.yaml

```yaml
# Системные настройки
system:
  limits:
    max_traders: 10
    max_concurrent_trades: 50

# База данных
database:
  host: "127.0.0.1"
  port: 5432
  name: "bot_trading_v3"

# Трейдеры (опционально)
traders:
  - id: "ml_trader_btc"
    enabled: false
    exchange: "bybit"
    strategy: "PatchTSTStrategy"
```

### config/traders/ml_trader_example.yaml

```yaml
id: "ml_trader_01"
enabled: true
exchange: "bybit"
symbol: "BTC/USDT"
strategy: "PatchTSTStrategy"

strategy_config:
  models:
    model_path: "models/saved/best_model.pth"
  trading:
    min_confidence: 0.70

risk_management:
  max_risk_per_trade: 0.02
  max_positions: 2
```

## Как добавить ML трейдера

### Способ 1: Через отдельный файл (рекомендуется)

1. **Создайте файл** `config/traders/my_ml_trader.yaml`:

```yaml
id: "ml_scalper_eth"
name: "ML ETH Scalper"
enabled: true
exchange: "binance"
symbol: "ETH/USDT"
strategy: "PatchTSTStrategy"

strategy_config:
  models:
    model_path: "models/eth_model.pth"
    scaler_path: "models/eth_scaler.pkl"

  trading:
    min_confidence: 0.75
    position_sizing_mode: "fixed"
    fixed_risk_pct: 0.01

risk_management:
  max_positions: 3
  stop_loss:
    enabled: true
    type: "dynamic"
    value: 0.015
```

2. **Перезапустите систему** или вызовите reload:

```python
await config_manager.reload_config()
```

### Способ 2: Через system.yaml

Добавьте в раздел `traders`:

```yaml
traders:
  - id: "ml_quick_trader"
    enabled: true
    exchange: "okx"
    symbol: "SOL/USDT"
    strategy: "PatchTSTStrategy"
    config_file: "config/traders/ml_quick.yaml"  # Опционально
```

### Способ 3: Программно через API

```bash
curl -X POST http://localhost:8080/api/traders \
  -H "Content-Type: application/json" \
  -d '{
    "id": "ml_api_trader",
    "name": "API ML Trader",
    "exchange": "bybit",
    "symbol": "DOGE/USDT",
    "strategy": "PatchTSTStrategy",
    "enabled": true
  }'
```

## Валидация конфигурации

Система автоматически валидирует конфигурации при загрузке:

```bash
# Проверить всю конфигурацию
python scripts/check_config.py

# Проверить конкретного трейдера
python scripts/check_config.py --trader ml_trader_01

# Валидировать файл
python scripts/check_config.py --validate config/traders/new_trader.yaml
```

## Важные моменты

### ✅ Нет хардкода

- Все настройки из конфигураций
- Переменные окружения для секретов
- Динамическая загрузка трейдеров

### ✅ Гибкость

- Трейдеры в отдельных файлах или в system.yaml
- Переопределение настроек на уровне трейдера
- Hot reload конфигураций

### ✅ Масштабируемость

- Добавление трейдеров без изменения кода
- Поддержка множественных стратегий
- Изоляция конфигураций трейдеров

### ⚠️ Обратите внимание

1. **Уникальность ID**: Каждый трейдер должен иметь уникальный `id`
2. **Обязательные поля**: `id`, `exchange`, `symbol`, `strategy`
3. **Переменные окружения**: API ключи через `.env`
4. **Валидация**: Всегда проверяйте конфигурацию перед запуском

## Примеры конфигураций для разных сценариев

### Консервативный ML трейдер

```yaml
id: "conservative_btc"
enabled: true
exchange: "bybit"
symbol: "BTC/USDT"
strategy: "PatchTSTStrategy"

strategy_config:
  trading:
    min_confidence: 0.80      # Очень высокая уверенность
    min_profit_probability: 0.85
    position_sizing_mode: "fixed"
    fixed_risk_pct: 0.005     # 0.5% риск

risk_management:
  max_positions: 1
  max_portfolio_risk: 0.02    # 2% общий риск
  stop_loss:
    type: "fixed"
    value: 0.01               # 1% stop loss
```

### Агрессивный ML скальпер

```yaml
id: "aggressive_scalper"
enabled: true
exchange: "binance"
symbol: "ETH/USDT"
strategy: "PatchTSTStrategy"

strategy_config:
  trading:
    min_confidence: 0.60      # Ниже порог
    position_sizing_mode: "kelly"
    kelly_safety_factor: 0.5

  timeframe_weights:
    15m: 0.50                 # Фокус на краткосрок
    1h: 0.30
    4h: 0.15
    12h: 0.05

risk_management:
  max_positions: 5
  max_risk_per_trade: 0.03    # 3% риск

execution:
  order_type: "market"        # Быстрое исполнение
```

### Мульти-таймфрейм ML трейдер

```yaml
id: "multi_tf_trader"
enabled: true
exchange: "okx"
symbol: "BTC/USDT"
strategy: "PatchTSTStrategy"

strategy_config:
  timeframe_weights:
    15m: 0.25    # Равномерное распределение
    1h: 0.25
    4h: 0.25
    12h: 0.25

  market_conditions:
    trending:
      timeframe_weights:
        4h: 0.40
        12h: 0.35
    ranging:
      timeframe_weights:
        15m: 0.45
        1h: 0.40
```

## Заключение

Система конфигурации BOT_AI_V3:

- ✅ Полностью конфигурируемая без хардкода
- ✅ Поддерживает множественных трейдеров
- ✅ Валидация на всех уровнях
- ✅ Гибкая и расширяемая архитектура

Для добавления ML трейдера просто создайте YAML файл в `config/traders/` и перезапустите систему.
