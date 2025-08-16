# ML Data Logging Enhancement - Документация по доработке

## 📋 Обзор доработки

**Дата:** 16 января 2025
**Версия:** 1.0.0
**Автор:** Claude AI Assistant
**Статус:** ✅ Завершено

### Цель доработки

Обеспечить полное логирование и сохранение в базу данных всех компонентов ML pipeline для последующего анализа и оценки качества каждого сигнала.

## 🎯 Решенные проблемы

1. **ProcessedMarketData не сохранялась** - таблица была пустой несмотря на наличие кода сохранения
2. **ML predictions сохранялись с symbol="UNKNOWN"** - невозможно было отследить для какого символа предсказание
3. **Не сохранялись полные входные признаки** - только хэш, что не позволяло анализировать входные данные
4. **Отсутствовала связь между таблицами** - сложно было проследить путь от входа до выхода

## 🔧 Внесенные изменения

### 1. Активация сохранения ProcessedMarketData

**Файл:** `ml/ml_signal_processor.py`
**Строки:** 1001-1006

```python
# БЫЛО: только вызов prepare_ml_input()

# СТАЛО:
# 2. Сначала рассчитываем и сохраняем индикаторы в БД
indicators = await self.indicator_calculator.calculate_indicators(
    symbol=symbol,
    ohlcv_df=ohlcv_df,
    save_to_db=True  # ВКЛЮЧАЕМ сохранение в processed_market_data
)

# 3. Затем готовим ML input
features_array, metadata = await self.indicator_calculator.prepare_ml_input(
    symbol=symbol,
    ohlcv_df=ohlcv_df,
    lookback=96,
)
```

### 2. Исправление передачи символа в ML predictions

**Файл:** `ml/ml_manager.py`
**Строки:** 286-295, 470-477

```python
# Добавлен параметр symbol в метод predict
async def predict(
    self,
    input_data: pd.DataFrame | np.ndarray,
    symbol: str | None = None  # НОВЫЙ ПАРАМЕТР
) -> dict[str, Any]:
    ...
    # Используем переданный symbol параметр
    if symbol:
        pass  # Используем переданный символ
    elif isinstance(input_data, pd.DataFrame) and "symbol" in input_data.columns:
        symbol = input_data["symbol"].iloc[-1]
    else:
        symbol = "UNKNOWN"
```

**Файл:** `ml/ml_signal_processor.py`
**Строка:** 1019

```python
# Передаем symbol при вызове predict
prediction = await self.ml_manager.predict(features_array, symbol=symbol)
```

### 3. Сохранение полного массива признаков

**Файл:** `ml/ml_prediction_logger.py`
**Строки:** 101-102

```python
prediction_record = {
    ...
    # Full arrays for detailed analysis
    'features_array': features.tolist() if features.size < 1000 else None,
    'model_outputs_raw': model_outputs.tolist() if model_outputs is not None else None,
}
```

## 📊 Структура сохраняемых данных

### ProcessedMarketData

```json
{
  "symbol": "BTCUSDT",
  "timestamp": 1737039600000,
  "ml_features": {/* 240 features */},
  "technical_indicators": {/* RSI, MACD, BB, etc */},
  "microstructure_features": {/* spread, imbalance, etc */}
}
```

### ML Predictions

```json
{
  "symbol": "BTCUSDT",
  "features_count": 240,
  "features_array": [/* all 240 feature values */],
  "predicted_return_15m": -0.0012,
  "direction_15m": "LONG",
  "signal_type": "LONG",
  "signal_confidence": 0.75
}
```

## 🔍 Проверка работоспособности

### SQL запросы для проверки

```sql
-- 1. Проверка ProcessedMarketData
SELECT
    symbol,
    datetime,
    jsonb_array_length(ml_features::jsonb) as ml_features_count,
    jsonb_object_keys(technical_indicators::jsonb) as tech_indicator
FROM processed_market_data
WHERE datetime > NOW() - INTERVAL '1 hour'
ORDER BY datetime DESC
LIMIT 10;

-- 2. Проверка ML predictions с символами
SELECT
    symbol,
    datetime,
    features_count,
    signal_type,
    signal_confidence,
    predicted_return_15m
FROM ml_predictions
WHERE symbol != 'UNKNOWN'
AND datetime > NOW() - INTERVAL '1 hour'
ORDER BY datetime DESC
LIMIT 10;

-- 3. Связка данных по времени
SELECT
    p.symbol,
    p.datetime,
    p.features_count,
    m.signal_type,
    m.signal_confidence,
    s.signal_type as final_signal
FROM processed_market_data p
LEFT JOIN ml_predictions m ON p.symbol = m.symbol
    AND ABS(EXTRACT(EPOCH FROM (p.datetime - m.datetime))) < 60
LEFT JOIN signals s ON p.symbol = s.symbol
    AND ABS(EXTRACT(EPOCH FROM (p.datetime - s.created_at))) < 60
WHERE p.datetime > NOW() - INTERVAL '1 hour'
ORDER BY p.datetime DESC;
```

### Python скрипт для проверки

```python
import asyncio
from database.connections.postgres import AsyncPGPool

async def verify_data_flow():
    # Проверка ProcessedMarketData
    processed = await AsyncPGPool.fetchrow("""
        SELECT COUNT(*) as cnt,
               COUNT(DISTINCT symbol) as symbols
        FROM processed_market_data
        WHERE datetime > NOW() - INTERVAL '10 minutes'
    """)
    print(f"ProcessedMarketData: {processed['cnt']} records, {processed['symbols']} symbols")

    # Проверка ML predictions
    predictions = await AsyncPGPool.fetchrow("""
        SELECT COUNT(*) as cnt,
               COUNT(CASE WHEN symbol != 'UNKNOWN' THEN 1 END) as valid
        FROM ml_predictions
        WHERE datetime > NOW() - INTERVAL '10 minutes'
    """)
    print(f"ML Predictions: {predictions['cnt']} total, {predictions['valid']} with valid symbols")

asyncio.run(verify_data_flow())
```

## 📈 Преимущества доработки

1. **Полная прослеживаемость** - можно отследить путь от входных данных до финального сигнала
2. **Анализ качества** - возможность оценить качество каждого компонента ML pipeline
3. **Отладка** - легче найти проблемы в случае некорректных предсказаний
4. **Оптимизация** - данные для анализа и улучшения модели
5. **Аудит** - полная история всех предсказаний и решений

## 🚀 Активация

Изменения вступают в силу автоматически при следующем запуске системы:

```bash
source venv/bin/activate
python3 unified_launcher.py --mode=ml
```

## 📝 Дополнительные рекомендации

1. **Настроить ротацию данных** - таблицы будут быстро расти, рекомендуется настроить удаление старых записей
2. **Создать индексы** - для ускорения запросов по symbol и datetime
3. **Мониторинг размера БД** - следить за ростом таблиц processed_market_data и ml_predictions
4. **Резервное копирование** - настроить регулярный бэкап важных данных

## 🔗 Связанные файлы

- `ml/ml_signal_processor.py` - основная логика обработки сигналов
- `ml/ml_manager.py` - менеджер ML моделей
- `ml/ml_prediction_logger.py` - логирование предсказаний
- `ml/realtime_indicator_calculator.py` - расчет индикаторов
- `database/models/market_data.py` - модели данных
- `database/models/ml_predictions.py` - модель предсказаний

## 📊 Метрики для мониторинга

После внедрения рекомендуется отслеживать:

- **Процент заполнения** ProcessedMarketData vs RawMarketData
- **Процент валидных символов** в ml_predictions (не UNKNOWN)
- **Размер данных** в features_array (должно быть 240)
- **Скорость роста таблиц** в МБ/день
- **Время выполнения** сохранения в БД

## ✅ Статус завершения

Все запланированные изменения внесены и готовы к использованию. Система будет автоматически сохранять полные данные ML pipeline при следующем запуске.
