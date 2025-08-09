# Real-Time ML система генерации торговых сигналов

## Обзор

Система генерации торговых сигналов в реальном времени с использованием ML модели UnifiedPatchTST. Ключевое отличие от традиционного подхода - индикаторы рассчитываются **в момент генерации сигнала**, а не заранее.

## Архитектура

### Компоненты системы

```
┌─────────────────┐     ┌────────────────┐     ┌─────────────────┐
│   DataLoader    │────▶│ RealTime       │────▶│ ML Signal       │
│ (OHLCV данные)  │     │ Indicator      │     │ Processor       │
└─────────────────┘     │ Calculator     │     └─────────────────┘
                        └────────────────┘              │
                                                       ▼
┌─────────────────┐     ┌────────────────┐     ┌─────────────────┐
│ Signal          │◀────│ Model          │◀────│ ML Manager      │
│ Scheduler       │     │ Adapter        │     │ (PatchTST)      │
└─────────────────┘     └────────────────┘     └─────────────────┘
```

### Поток данных

1. **Загрузка OHLCV** → `raw_market_data` таблица
2. **Расчет индикаторов** → on-demand при генерации сигнала
3. **ML предсказание** → UnifiedPatchTST модель
4. **Адаптация выходов** → торговые сигналы
5. **Сохранение** → `processed_market_data` + `signals` таблицы

## Ключевые файлы

### 1. RealTimeIndicatorCalculator (`ml/realtime_indicator_calculator.py`)

Рассчитывает 240+ технических индикаторов в реальном времени:

```python
calculator = RealTimeIndicatorCalculator()

# Расчет индикаторов для символа
indicators = await calculator.calculate_indicators(
    symbol='BTCUSDT',
    ohlcv_df=df,  # Минимум 240 свечей
    save_to_db=True
)

# Подготовка данных для ML модели
features_array, metadata = await calculator.prepare_ml_input(
    symbol='BTCUSDT',
    ohlcv_df=df,
    lookback=96  # Временное окно для модели
)
```

### 2. MLSignalProcessor (`ml/ml_signal_processor.py`)

Обновлен для работы с real-time индикаторами:

```python
processor = MLSignalProcessor(ml_manager, config)

# Генерация сигнала в реальном времени
signal = await processor.process_realtime_signal(
    symbol='BTCUSDT',
    exchange='bybit',
    lookback_minutes=3600  # 240 свечей * 15 минут
)

# Пакетная генерация для нескольких символов
signals = await processor.generate_signals_for_symbols(
    symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
    exchange='bybit'
)
```

### 3. ModelOutputAdapter (`ml/model_adapter.py`)

Преобразует 20 выходов модели в торговые сигналы:

```python
adapter = ModelOutputAdapter()

# Адаптация выходов модели
predictions = adapter.adapt_model_outputs(
    raw_outputs=model_output,  # [batch_size, 20]
    symbols=['BTCUSDT']
)

# Расчет уровней SL/TP
levels = adapter.calculate_trading_levels(
    current_price=50000,
    predictions=predictions['BTCUSDT'],
    risk_tolerance=0.02  # 2% риск
)
```

### 4. SignalScheduler (`ml/signal_scheduler.py`)

Планировщик для периодической генерации сигналов:

```python
scheduler = SignalScheduler()
await scheduler.initialize()
await scheduler.start()

# Добавление/удаление символов на лету
await scheduler.add_symbol('SOLUSDT')
await scheduler.remove_symbol('BNBUSDT')

# Получение статуса
status = await scheduler.get_status()
```

## Конфигурация

### config/ml/ml_config.yaml

```yaml
ml:
  enabled: true
  symbols:
    - BTCUSDT
    - ETHUSDT
    - BNBUSDT
    # ... еще 47 символов

  signal_interval_seconds: 60  # Генерация каждую минуту
  default_exchange: bybit

  # Пороги для принятия решений
  min_confidence: 0.65
  min_signal_strength: 0.3
  risk_tolerance: MEDIUM

  # Настройки модели
  model:
    path: models/saved/best_model.pth
    device: cuda
    lookback: 96
    features: 240

  # Кеширование
  cache_ttl: 60  # секунд
  save_signals: true
```

## База данных

### Таблица processed_market_data

Хранит рассчитанные индикаторы:

```sql
-- JSONB поля для гибкого хранения
technical_indicators    -- RSI, MACD, BB, и т.д.
microstructure_features -- spread, imbalance, pressure
ml_features            -- Все 240+ признаков

-- Индексы для быстрого поиска
CREATE INDEX idx_processed_technical_indicators
ON processed_market_data USING gin(technical_indicators);
```

## Использование

### 1. Запуск планировщика сигналов

```bash
# Автономный запуск
python -m ml.signal_scheduler

# Или через main.py с включенной ML системой
python main.py --enable-ml
```

### 2. Тестирование системы

```bash
# Полный тест всех компонентов
python scripts/test_realtime_signals.py

# Тест конкретного символа
python scripts/test_ml_signal.py --symbol BTCUSDT
```

### 3. Мониторинг

```python
# API endpoint для статуса
GET /api/ml/status

# WebSocket для real-time сигналов
ws://localhost:8080/ws/ml-signals
```

## Оптимизация производительности

### 1. Кеширование индикаторов

- TTL 60 секунд для рассчитанных индикаторов
- Инкрементальное обновление при новых свечах
- Параллельный расчет для нескольких символов

### 2. Батчевая обработка

```python
# Обработка нескольких символов одновременно
results = await calculator.calculate_indicators_batch(
    symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
    ohlcv_data={symbol: df for symbol, df in data.items()}
)
```

### 3. Оптимизация БД

- Партиционирование таблиц по времени
- JSONB индексы для быстрого доступа к индикаторам
- Асинхронные запросы через asyncpg

## Мониторинг и алерты

### Метрики

- `ml_signals_generated_total` - общее количество сигналов
- `ml_signal_generation_duration_seconds` - время генерации
- `ml_model_prediction_errors_total` - ошибки предсказаний
- `ml_confidence_histogram` - распределение уверенности

### Алерты

1. **Низкая успешность сигналов** - < 40% за час
2. **Высокая латентность** - > 5 секунд на генерацию
3. **Ошибки модели** - > 10 ошибок подряд
4. **Недостаток данных** - < 240 свечей для символа

## Преимущества подхода

1. **Актуальность** - индикаторы всегда свежие
2. **Гибкость** - легко добавлять новые индикаторы
3. **Масштабируемость** - параллельная обработка
4. **Надежность** - изоляция ошибок по символам
5. **Прозрачность** - все расчеты сохраняются в БД

## Дальнейшее развитие

1. **A/B тестирование** различных наборов признаков
2. **Адаптивные пороги** на основе рыночных условий
3. **Ансамбль моделей** для повышения точности
4. **Streaming обработка** через WebSocket
5. **Edge deployment** для минимальной латентности
