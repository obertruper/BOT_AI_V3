# PatchTST Model для BOT Trading v3

## Описание

Адаптированная версия унифицированной PatchTST модели для многозадачного прогнозирования в криптотрейдинге.

## Архитектура

### Входные данные

- **240 признаков**: OHLCV + технические индикаторы
- **Контекстное окно**: 96 временных шагов (24 часа при 15-минутных свечах)
- **Patch-based подход**: разбиение последовательности на патчи для эффективной обработки

### Выходные данные (20 переменных)

1. **Future Returns (0-3)**: Прогноз доходности на 15м, 1ч, 4ч, 12ч
2. **Directions (4-7)**: Направление движения (LONG=0, SHORT=1, FLAT=2)
3. **Long Levels (8-11)**: Вероятность достижения уровней прибыли для лонг позиций
4. **Short Levels (12-15)**: Вероятность достижения уровней прибыли для шорт позиций
5. **Risk Metrics (16-19)**: Максимальные просадки и ралли

## Использование

### Создание модели

```python
from ml.logic.patchtst_model import create_unified_model

config = {
    'model': {
        'input_size': 240,
        'output_size': 20,
        'context_window': 96,
        'patch_len': 16,
        'stride': 8,
        'd_model': 256,
        'n_heads': 4,
        'e_layers': 3,
        'd_ff': 512,
        'dropout': 0.1
    }
}

model = create_unified_model(config)
```

### Инференс

```python
import torch

# Подготовка данных
market_data = torch.randn(batch_size, 96, 240)

# Предсказание
model.eval()
with torch.no_grad():
    predictions = model(market_data)
```

### Обучение

```python
from ml.logic.patchtst_model import DirectionalMultiTaskLoss

# Loss функция
criterion = DirectionalMultiTaskLoss(config)

# Обучение
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

outputs = model(inputs)
loss = criterion(outputs, targets)
loss.backward()
optimizer.step()
```

## Ключевые особенности

1. **Multi-task Learning**: Одновременное обучение на нескольких задачах
2. **Patch-based Processing**: Эффективная обработка длинных последовательностей
3. **Temperature Scaling**: Калибровка уверенности предсказаний
4. **Focal Loss**: Борьба с дисбалансом классов в направлениях
5. **Reversible Instance Normalization**: Стабилизация обучения на финансовых данных

## Конфигурация

### Параметры модели

- `input_size`: Количество входных признаков (240)
- `context_window`: Длина временного окна (96)
- `patch_len`: Размер патча (16)
- `stride`: Шаг окна патча (8)
- `d_model`: Размерность внутреннего представления (256)
- `n_heads`: Количество голов attention (4)
- `e_layers`: Количество слоев энкодера (3)

### Параметры loss

- `task_weights`: Веса для разных типов задач
- `class_weights`: Веса классов для направлений [LONG, SHORT, FLAT]
- `large_move_weight`: Дополнительный вес для крупных движений
- `focal_alpha`, `focal_gamma`: Параметры focal loss

## Интеграция с BOT Trading v3

Модель интегрируется через:

1. **StrategyManager**: Использование предсказаний для генерации сигналов
2. **RiskManager**: Использование risk metrics для управления рисками
3. **SignalProcessor**: Обработка direction predictions для торговых решений

## Производительность

- Поддержка GPU через CUDA
- Batch processing для эффективного инференса
- Оптимизированная архитектура transformer
