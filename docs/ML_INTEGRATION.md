# ML Integration с UnifiedPatchTST моделью

## Обзор

В проект BOT_AI_V3 интегрирована продвинутая ML модель UnifiedPatchTST из проекта LLM TRANSFORM для предсказания движений криптовалют.

## Характеристики модели

- **Архитектура**: UnifiedPatchTST (Patch Time Series Transformer)
- **Входы**: 240 признаков (OHLCV + технические индикаторы + микроструктура)
- **Выходы**: 20 целевых переменных
- **Контекстное окно**: 96 временных шагов (24 часа при 15-минутных свечах)
- **F1 Score**: 0.414
- **Win Rate**: 46.6%

## Структура ML компонентов

```
BOT_AI_V3/
├── ml/
│   ├── logic/
│   │   ├── patchtst_model.py      # Адаптированная модель PatchTST
│   │   ├── feature_engineering.py # Генерация 240+ признаков
│   │   └── indicator_integration.py # Интеграция с индикаторами
│   └── models/
├── models/saved/
│   ├── best_model_20250728_215703.pth # Обученная модель (45MB)
│   ├── data_scaler.pkl                # Scaler для нормализации
│   └── config.pkl                     # Конфигурация модели
├── strategies/ml_strategy/
│   ├── patchtst_strategy.py    # ML торговая стратегия
│   ├── model_manager.py        # Управление моделями
│   └── patchtst_config.yaml    # Конфигурация стратегии
└── config/ml/
    └── ml_config.yaml          # Основная ML конфигурация
```

## Выходы модели (20 переменных)

### 1. Future Returns (0-3)

- `future_return_15m`: Прогноз доходности на 15 минут
- `future_return_1h`: Прогноз доходности на 1 час
- `future_return_4h`: Прогноз доходности на 4 часа
- `future_return_12h`: Прогноз доходности на 12 часов

### 2. Направления движения (4-7)

- `direction_15m`: Направление на 15 мин (0=LONG, 1=SHORT, 2=FLAT)
- `direction_1h`: Направление на 1 час
- `direction_4h`: Направление на 4 часа
- `direction_12h`: Направление на 12 часов

### 3. Вероятности LONG уровней (8-11)

- `long_will_reach_1pct_4h`: Вероятность +1% за 4 часа
- `long_will_reach_2pct_4h`: Вероятность +2% за 4 часа
- `long_will_reach_3pct_12h`: Вероятность +3% за 12 часов
- `long_will_reach_5pct_12h`: Вероятность +5% за 12 часов

### 4. Вероятности SHORT уровней (12-15)

- `short_will_reach_1pct_4h`: Вероятность -1% за 4 часа
- `short_will_reach_2pct_4h`: Вероятность -2% за 4 часа
- `short_will_reach_3pct_12h`: Вероятность -3% за 12 часов
- `short_will_reach_5pct_12h`: Вероятность -5% за 12 часов

### 5. Риск-метрики (16-19)

- `max_drawdown_1h`: Максимальная просадка за 1 час
- `max_rally_1h`: Максимальный рост за 1 час
- `max_drawdown_4h`: Максимальная просадка за 4 часа
- `max_rally_4h`: Максимальный рост за 4 часа

## Использование

### 1. Подготовка данных

```python
from ml.logic.feature_engineering import FeatureEngineer

# Создание инженера признаков
fe = FeatureEngineer()

# Подготовка признаков
features = fe.create_features(market_data)
```

### 2. Загрузка и использование модели

```python
from ml.logic.patchtst_model import create_unified_model
import torch
import pickle

# Загрузка конфигурации
with open('models/saved/config.pkl', 'rb') as f:
    config = pickle.load(f)

# Создание модели
model = create_unified_model(config)

# Загрузка весов
model.load_state_dict(torch.load('models/saved/best_model_20250728_215703.pth'))
model.eval()

# Предсказание
with torch.no_grad():
    predictions = model(features_tensor)
```

### 3. Запуск ML стратегии

```bash
# Dry run (тестовый режим)
python scripts/run_ml_strategy.py --symbol BTCUSDT

# Live режим (реальная торговля)
python scripts/run_ml_strategy.py --symbol BTCUSDT --live
```

## Алгоритм торговли

1. **Подготовка данных**: FeatureEngineer генерирует 240+ признаков из последних 96 свечей
2. **Предсказание**: Модель выдает 20 предсказаний
3. **Анализ сигналов**:
   - Взвешенное голосование по 4 таймфреймам
   - Учет вероятностей достижения уровней
   - Оценка рисков
4. **Генерация сигнала**: LONG/SHORT/FLAT с уверенностью
5. **Risk Management**:
   - Адаптивный stop-loss на основе предсказанных рисков
   - Take-profit на основе вероятностей уровней
   - Размер позиции через Kelly Criterion

## Настройка параметров

Основные параметры в `strategies/ml_strategy/patchtst_config.yaml`:

- `min_confidence`: Минимальная уверенность для торговли (0.6)
- `min_probability`: Минимальная вероятность достижения TP (0.65)
- `timeframe_weights`: Веса для разных таймфреймов
- `risk_multipliers`: Множители для расчета SL из предсказанных рисков

## Мониторинг производительности

ML стратегия автоматически логирует:

- Все предсказания и сигналы
- Метрики производительности модели
- Статистику по направлениям и уверенности
- Реализованный P&L

## Обновление модели

При появлении новой версии модели:

1. Скопировать новые файлы в `models/saved/`
2. Обновить `config.pkl` через `scripts/prepare_model_config.py`
3. Перезапустить стратегию

## Troubleshooting

### Модель предсказывает только FLAT

- Проверьте порог уверенности в конфигурации
- Убедитесь что данные правильно нормализованы
- Проверьте качество входных признаков

### Низкая производительность

- Используйте GPU если доступен
- Уменьшите batch_size
- Включите кэширование предсказаний

### Ошибки загрузки модели

- Проверьте наличие всех файлов (model.pth, scaler.pkl, config.pkl)
- Убедитесь в совместимости версий PyTorch
