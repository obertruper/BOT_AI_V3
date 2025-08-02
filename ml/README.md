# ML Components для BOT_AI_V3

## Обзор

Модуль машинного обучения для прогнозирования движений криптовалют на основе UnifiedPatchTST архитектуры.

## Структура

```
ml/
├── logic/                          # Основная логика ML
│   ├── patchtst_model.py          # UnifiedPatchTST модель
│   ├── feature_engineering.py     # Генерация 240+ признаков
│   └── indicator_integration.py   # Интеграция с индикаторами
├── models/                        # Модели (пустая, файлы в models/saved/)
└── README.md                      # Этот файл
```

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install torch numpy pandas scikit-learn ta
```

### 2. Подготовка файлов модели

Убедитесь что следующие файлы находятся в `models/saved/`:

- `best_model_20250728_215703.pth` - веса модели (45MB)
- `data_scaler.pkl` - scaler для нормализации
- `config.pkl` - конфигурация модели

### 3. Использование

```python
from ml.logic.patchtst_model import create_unified_model
from ml.logic.feature_engineering import FeatureEngineer
import torch
import pickle

# Загрузка модели
with open('models/saved/config.pkl', 'rb') as f:
    config = pickle.load(f)

model = create_unified_model(config)
model.load_state_dict(torch.load('models/saved/best_model_20250728_215703.pth'))
model.eval()

# Подготовка данных
fe = FeatureEngineer()
features = fe.create_features(market_data)

# Предсказание
with torch.no_grad():
    predictions = model(features_tensor)
```

## Архитектура модели

### UnifiedPatchTST

- **Базовая архитектура**: Patch Time Series Transformer
- **Входы**: 240 признаков × 96 временных шагов
- **Patch размер**: 16 с шагом 8
- **Transformer**: 3 слоя, 4 головы внимания, d_model=256
- **Выходы**: 20 целевых переменных

### Feature Engineering

- **Базовые**: OHLCV, returns, ratios
- **Технические**: RSI, MACD, Bollinger Bands, ATR и др.
- **Микроструктура**: order flow, volume profile
- **Статистические**: volatility, skewness, correlations
- **Временные**: hour, day of week, month effects

## Интеграция со стратегией

ML компоненты интегрированы с торговой стратегией в `strategies/ml_strategy/`:

- `patchtst_strategy.py` - основная стратегия
- `model_manager.py` - управление моделями
- `patchtst_config.yaml` - конфигурация

Запуск стратегии:

```bash
python scripts/run_ml_strategy.py --symbol BTCUSDT
```

## Производительность

- **F1 Score**: 0.414
- **Win Rate**: 46.6%
- **Inference время**: ~50ms на батч
- **Требования памяти**: ~500MB (модель + данные)

## Разработка

### Добавление новых признаков

1. Отредактируйте `feature_engineering.py`
2. Добавьте метод в класс `FeatureEngineer`
3. Обновите общее количество признаков в конфигурации

### Обновление модели

1. Поместите новые файлы в `models/saved/`
2. Обновите `config.pkl` через `scripts/prepare_model_config.py`
3. Перезапустите стратегию

### Тестирование

```bash
# Unit тесты
pytest tests/unit/ml/

# Тест feature engineering
pytest tests/unit/ml/test_feature_engineering.py

# Тест модели
pytest tests/unit/ml/test_patchtst_model.py
```

## Документация

- [Полная документация ML интеграции](../docs/ML_INTEGRATION.md)
- [README Feature Engineering](logic/README_FEATURE_ENGINEERING.md)
- [README PatchTST модели](logic/README.md)
- [README ML стратегии](../strategies/ml_strategy/README.md)
