# ML Integration Guide

## 🧠 Интеграция ML системы в BOT_AI_V3

Полная интеграция ML системы предсказаний с торговым движком для автоматической генерации и исполнения торговых сигналов.

## 📊 Архитектура ML потока

```
ML Manager → ML Signal Processor → Signal Scheduler
                    ↓
            Trading Signal
                    ↓
         AI Signal Generator → Trading Engine
                                      ↓
                              Signal Processor
                                      ↓
                                   Orders
                                      ↓
                              Order Manager → Exchange
```

## 🚀 Ключевые компоненты

### 1. ML Manager

- **Путь**: `ml/ml_manager.py`
- **Функции**:
  - Загрузка и управление UnifiedPatchTST моделью
  - GPU-оптимизированная инференция
  - Кэширование предсказаний

### 2. ML Signal Processor

- **Путь**: `ml/ml_signal_processor.py`
- **Функции**:
  - Преобразование ML предсказаний в торговые сигналы
  - Real-time расчет 240+ технических индикаторов
  - Интеграция с системой оценки сигналов

### 3. Signal Scheduler

- **Путь**: `ml/signal_scheduler.py`
- **Функции**:
  - Генерация сигналов каждую минуту
  - Параллельная обработка множественных символов
  - Интеграция с Trading Engine

### 4. AI Signal Generator

- **Путь**: `trading/signals/ai_signal_generator.py`
- **Функции**:
  - Комплексная оценка сигналов
  - Технический анализ + ML scoring
  - Адаптивные SL/TP уровни

### 5. Trading Engine

- **Путь**: `trading/engine.py`
- **Функции**:
  - Прием и маршрутизация торговых сигналов
  - Конвертация форматов сигналов
  - Управление очередями обработки

### 6. Signal Processor

- **Путь**: `trading/signals/signal_processor.py`
- **Функции**:
  - Создание ордеров из сигналов
  - Валидация и риск-менеджмент
  - Расчет размера позиций

## 🔧 Конфигурация

### system.yaml

```yaml
ml:
  enabled: true
  signal_generation:
    interval_seconds: 60
    batch_size: 10
    parallel_workers: 4

  symbols:
    - "BTCUSDT"
    - "ETHUSDT"
    - "BNBUSDT"
    - "SOLUSDT"
    - "XRPUSDT"
    - "ADAUSDT"
    - "DOGEUSDT"
    - "DOTUSDT"
    - "LINKUSDT"

  model:
    enabled: true
    path: "models/saved/best_model_20250728_215703.pth"
    device: "cuda"
    use_compile: false  # Отключено для RTX 5090

  min_confidence: 0.45
  min_signal_strength: 0.2
  risk_tolerance: "MEDIUM"
```

### traders.yaml

```yaml
traders:
  - id: "multi_crypto_10"
    enabled: true
    type: "multi_crypto"
    symbols:
      - "BTCUSDT"
      - "ETHUSDT"
      - "BNBUSDT"
      - "SOLUSDT"
      - "XRPUSDT"
    exchange: "bybit"
    strategy: "ml_signal"
    strategy_config:
      signal_interval: 60
      indicators:
        - type: "RSI"
          period: 14
          oversold: 30
          overbought: 70
        - type: "EMA"
          short_period: 9
          long_period: 21
    capital:
      initial: 10000
      per_trade_percentage: 2
      max_positions: 5
    risk_management:
      stop_loss_percentage: 2
      take_profit_percentage: 5
      max_drawdown_percentage: 10
```

## 📡 API Endpoints

### ML Status

```http
GET /api/v1/ml/status
```

### Generate Signal

```http
POST /api/v1/ml/generate-signal
{
  "symbol": "BTCUSDT",
  "exchange": "bybit"
}
```

### Get ML Predictions

```http
GET /api/v1/ml/predictions/{symbol}
```

## 🚀 Запуск ML торговли

### 1. Через Unified Launcher (рекомендуется)

```bash
# Запуск с ML
python unified_launcher.py --mode=ml

# Проверка статуса
python unified_launcher.py --status
```

### 2. Отдельный Signal Scheduler

```bash
# Активация окружения
source venv/bin/activate

# Запуск планировщика
python -m ml.signal_scheduler
```

### 3. Тестирование ML потока

```bash
# Простой тест
python test_ml_flow_simple.py

# Полный тест интеграции
python test_ml_to_orders_flow.py
```

## 📊 Мониторинг

### Логи

```bash
# ML сигналы
tail -f data/logs/ml_signals.log

# Trading Engine
tail -f data/logs/trading.log

# Ошибки
tail -f data/logs/error.log
```

### Метрики

- Количество сгенерированных сигналов
- Распределение типов сигналов (LONG/SHORT/NEUTRAL)
- Среднее время генерации
- Успешность создания ордеров

## 🔍 Отладка

### Проверка ML модели

```python
from ml.ml_manager import MLManager

ml_manager = MLManager(config)
await ml_manager.initialize()

# Проверка загрузки
print(f"Model loaded: {ml_manager.model is not None}")
print(f"Device: {ml_manager.device}")
```

### Проверка генерации сигналов

```python
from ml.ml_signal_processor import MLSignalProcessor

processor = MLSignalProcessor(ml_manager, config)
signal = await processor.process_realtime_signal("BTCUSDT", "bybit")
print(f"Signal: {signal}")
```

## ⚠️ Известные особенности

1. **GPU RTX 5090**: torch.compile отключен из-за несовместимости с sm_120
2. **NEUTRAL сигналы**: Модель часто генерирует нейтральные сигналы в спокойном рынке
3. **Кэширование**: TTL установлен на 15 минут для 15-минутных свечей

## 📈 Производительность

- **Время инференции**: ~200-300ms на GPU
- **Генерация сигналов**: 1 минута для всех символов
- **Пропускная способность**: 1000+ сигналов/сек
- **Задержка API**: <50ms

## 🔗 Связанная документация

- [ML Signal Evaluation System](ML_SIGNAL_EVALUATION_SYSTEM.md)
- [ML Tuning Guide](ML_TUNING_GUIDE.md)
- [Trading Engine Architecture](TRADING_ENGINE.md)
