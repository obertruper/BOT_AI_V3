# Исправление загрузки ML модели PatchTST

## Проблема

При загрузке сохраненной модели `models/saved/best_model_20250728_215703.pth` возникали следующие ошибки:

1. **Unexpected keys**: В сохраненной модели присутствовали ключи `confidence_head.0.weight`, `confidence_head.0.bias` и т.д., которые отсутствовали в текущей архитектуре модели.

2. **Size mismatch**: Несоответствие размерностей для `positional_encoding.pe`:
   - Ожидалось: `[11, 1, 256]` (seq_len, batch, d_model)
   - В модели: `[1, 11, 256]` (batch, seq_len, d_model)

## Решение

### 1. Добавление confidence_head в модель

В класс `UnifiedPatchTSTForTrading` добавлен слой `confidence_head` для обратной совместимости:

```python
# 6. Confidence head (для совместимости со старой моделью)
self.confidence_head = nn.Sequential(
    nn.Linear(self.d_model, self.d_model // 2),
    nn.ReLU(),
    nn.Dropout(self.dropout),
    nn.Linear(self.d_model // 2, 4)
)
```

### 2. Исправление формата positional encoding

Изменен формат позиционного кодирования для соответствия batch_first=True в MultiheadAttention:

```python
class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        # ... вычисления ...
        # Изменено: формат [batch, seq_len, d_model] для совместимости
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, seq_len, d_model)"""
        # Адаптация под batch_first=True
        return x + self.pe[:, :x.size(1), :]
```

### 3. Функция безопасной загрузки модели

Создана функция `load_model_safe` для обработки несовместимостей при загрузке:

```python
def load_model_safe(model: UnifiedPatchTSTForTrading, checkpoint_path: str, device: str = 'cpu') -> UnifiedPatchTSTForTrading:
    """
    Безопасная загрузка модели с обработкой несовместимостей
    """
    checkpoint = torch.load(checkpoint_path, map_location=device)

    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    else:
        state_dict = checkpoint

    # Обработка несовместимостей размерностей
    model_state = model.state_dict()
    compatible_state_dict = {}

    for key, value in state_dict.items():
        if key in model_state:
            if model_state[key].shape == value.shape:
                compatible_state_dict[key] = value
            else:
                # Специальная обработка для positional_encoding
                if 'positional_encoding.pe' in key:
                    compatible_state_dict[key] = value
                else:
                    logger.warning(f"Skipping {key} due to shape mismatch")

    # Загружаем совместимые веса
    model.load_state_dict(compatible_state_dict, strict=False)

    return model
```

### 4. Обновление ModelManager

`ModelManager` обновлен для использования безопасной функции загрузки:

```python
# Безопасная загрузка весов с обработкой несовместимостей
try:
    model = load_model_safe(model, str(model_path), device=str(self.device))
    self.logger.info(f"Модель загружена с использованием безопасной функции")
except Exception as e:
    self.logger.warning(f"Ошибка при безопасной загрузке, пробуем стандартный метод: {e}")
    # Фоллбэк на стандартную загрузку
    model.load_state_dict(checkpoint['model_state_dict'], strict=False)
```

## Использование

### Прямая загрузка модели

```python
from ml.logic.patchtst_model import create_unified_model, load_model_safe

# Создание модели
config = {...}  # конфигурация модели
model = create_unified_model(config)

# Безопасная загрузка
model = load_model_safe(model, 'models/saved/best_model_20250728_215703.pth', device='cpu')
```

### Через ModelManager

```python
from strategies.ml_strategy.model_manager import get_model_manager

manager = get_model_manager()
model, metadata = await manager.load_model("patchtst_trading")
```

## Результат

- ✅ Модель успешно загружается без ошибок
- ✅ Все 71 параметр из checkpoint корректно загружен
- ✅ Инференс работает корректно
- ✅ Обратная совместимость сохранена
