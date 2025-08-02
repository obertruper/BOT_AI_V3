# Feature Engineering для BOT_AI_V3

## Обзор

Модуль `feature_engineering.py` предоставляет комплексную систему генерации признаков для машинного обучения в криптотрейдинге. Создает 240+ признаков из OHLCV данных и 20 целевых переменных для обучения моделей.

## Основные компоненты

### 1. FeatureEngineer

Основной класс для генерации признаков:

```python
from ml.logic.feature_engineering import FeatureEngineer, FeatureConfig

# Создание с настройками по умолчанию
engineer = FeatureEngineer()

# Создание с кастомной конфигурацией
config = FeatureConfig(
    sma_periods=[10, 20, 50],
    ema_periods=[10, 20, 50],
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9
)
engineer = FeatureEngineer(config)
```

### 2. Группы признаков

#### Базовые OHLCV признаки (20)

- Логарифмические доходности
- Ценовые соотношения (high/low, close/open)
- Характеристики свечей (размер, тело, тени)
- VWAP и отношения к VWAP

#### Технические индикаторы (80)

- Moving Averages: SMA, EMA
- Осцилляторы: RSI, Stochastic, Williams %R
- Трендовые: MACD, ADX, Parabolic SAR
- Волатильность: Bollinger Bands, ATR, Keltner Channels
- Объем: MFI, CMF, OBV

#### Объемные признаки (30)

- Объемные соотношения и скользящие средние
- Направленный объем и дисбаланс
- On-Balance Volume (OBV)
- Money Flow Index (MFI)
- Chaikin Money Flow

#### Статистические признаки (40)

- Волатильность за разные периоды
- Skewness и Kurtosis доходностей
- Z-scores для цены и объема
- Percentile ranks
- Корреляции

#### Микроструктурные признаки (30)

- Спред high-low
- Ценовое воздействие (price impact)
- Амихуд неликвидность
- Kyle lambda
- Реализованная волатильность

#### Временные признаки (20)

- Час, день недели, месяц
- Торговые сессии (азиатская, европейская, американская)
- Циклические признаки (sin/cos трансформации)

#### Паттерны и сигналы (20)

- Сжатие волатильности (squeeze)
- Дивергенции RSI/MACD
- Структура тренда
- Моментум и ускорение
- Всплески объема

### 3. Целевые переменные (20)

#### Базовые возвраты (4)

- `future_return_15m`: Доходность через 15 минут
- `future_return_1h`: Доходность через 1 час
- `future_return_4h`: Доходность через 4 часа
- `future_return_12h`: Доходность через 12 часов

#### Направление движения (4)

- `direction_15m`: UP/DOWN/FLAT через 15 минут
- `direction_1h`: UP/DOWN/FLAT через 1 час
- `direction_4h`: UP/DOWN/FLAT через 4 часа
- `direction_12h`: UP/DOWN/FLAT через 12 часов

#### Достижение уровней LONG (4)

- `long_will_reach_1pct_4h`: Достигнет ли +1% за 4 часа
- `long_will_reach_2pct_4h`: Достигнет ли +2% за 4 часа
- `long_will_reach_3pct_12h`: Достигнет ли +3% за 12 часов
- `long_will_reach_5pct_12h`: Достигнет ли +5% за 12 часов

#### Достижение уровней SHORT (4)

- `short_will_reach_1pct_4h`: Достигнет ли -1% за 4 часа
- `short_will_reach_2pct_4h`: Достигнет ли -2% за 4 часа
- `short_will_reach_3pct_12h`: Достигнет ли -3% за 12 часов
- `short_will_reach_5pct_12h`: Достигнет ли -5% за 12 часов

#### Риск-метрики (4)

- `max_drawdown_1h`: Максимальная просадка за 1 час
- `max_drawdown_4h`: Максимальная просадка за 4 часа
- `max_rally_1h`: Максимальный рост за 1 час
- `max_rally_4h`: Максимальный рост за 4 часа

## Использование

### Базовый пример

```python
import pandas as pd
from ml.logic.feature_engineering import FeatureEngineer

# Загрузка OHLCV данных
df = pd.read_csv('ohlcv_data.csv')

# Создание признаков
engineer = FeatureEngineer()
features_df = engineer.create_features(df)

# Создание целевых переменных
features_df = engineer.create_target_variables(features_df)

# Получение списка признаков
feature_names = engineer.get_feature_names()
print(f"Создано {len(feature_names)} признаков")
```

### Интеграция с индикаторами проекта

```python
from ml.logic.indicator_integration import FeatureEngineerWithIndicators
from strategies.indicator_strategy.indicators.manager import IndicatorManager

# Создание с поддержкой индикаторов
indicator_manager = IndicatorManager(config)
engineer = FeatureEngineerWithIndicators(
    config=feature_config,
    indicator_manager=indicator_manager
)

# Генерация признаков включая индикаторы
features_df = engineer.create_features(df)

# Создание ансамблевых признаков
features_df = engineer.create_ensemble_features(features_df)
```

### Подготовка данных для обучения

```python
from ml.logic.feature_engineering_example import prepare_features_for_training

# Подготовка данных для множества символов
features_df, feature_names = await prepare_features_for_training(
    symbols=['BTCUSDT', 'ETHUSDT'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 7, 1),
    config=config
)
```

### Подготовка данных для предсказания

```python
from ml.logic.feature_engineering_example import prepare_features_for_prediction

# Подготовка признаков для реального времени
prediction_features = await prepare_features_for_prediction(
    symbol='BTCUSDT',
    data=recent_ohlcv_data,  # Минимум 100 свечей
    feature_names=feature_names,  # Из обученной модели
    config=config  # Та же конфигурация что при обучении
)
```

## Важные особенности

### 1. Безопасное деление

Все операции деления выполняются через `safe_divide()` для предотвращения деления на ноль и обработки экстремальных значений.

### 2. Обработка пропущенных значений

- Технические индикаторы заполняются методом forward-fill
- Остальные признаки заполняются медианой
- Inf значения заменяются на NaN, затем на 0

### 3. Предотвращение утечки данных

- Все признаки рассчитываются только на исторических данных
- Целевые переменные используют только будущие данные
- Никаких look-ahead bias в расчетах

### 4. Масштабируемость

- Поддержка множественных символов
- Эффективные векторизованные операции
- Кеширование для повторных расчетов

## Требования

- pandas >= 1.3.0
- numpy >= 1.21.0
- ta (Technical Analysis library)
- scikit-learn (для анализа важности признаков)
- structlog (для логирования)

## Производительность

- Создание признаков для 1000 свечей: ~0.5 сек
- Создание признаков для 10,000 свечей: ~3 сек
- Память: ~200 MB на 100,000 свечей с полным набором признаков

## Рекомендации

1. **Выбор признаков**: Не все 240 признаков нужны для каждой модели. Используйте feature importance для отбора.

2. **Нормализация**: Признаки не нормализованы по умолчанию. Применяйте StandardScaler или RobustScaler перед обучением.

3. **Временные окна**: Для стабильных индикаторов нужно минимум 100 свечей истории.

4. **Мультивалютность**: При работе с несколькими символами группируйте расчеты по символу.

5. **Валидация**: Всегда используйте walk-forward валидацию для предотвращения переобучения.
