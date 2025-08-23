# Удалённые комментарии при рефакторинге БД - 23 августа 2025

## trading/engine.py

### Строка 23-25 (удалено):
```python
# from database.repositories.signal_repository import SignalRepository  # Старый репозиторий с дублированием
from database.repositories.signal_repository_fixed import (
    SignalRepositoryFixed as SignalRepository,  # Исправленный
)
```
**Заменено на:** Прямой импорт из signal_repository

### Строка 389:
```python
# await self.signal_processor.start()  # Отключен
```

### Строка 445:
```python
# await self.signal_processor.stop()  # Отключен
```

## ml/ml_manager.py

### Строки 47-48:
```python
# torch.backends.cuda.matmul.allow_tf32 = True  # Deprecated
# torch.backends.cudnn.allow_tf32 = True  # Deprecated
```

## core/system/smart_data_manager.py

### Строка 481:
```python
# Старый формат - массив
```

### Строка 515:
```python
# Старый формат - массив
```

## database/connections/__init__.py

### Экспортируемая функция (удалена из экспорта):
```python
get_async_db,  # Устаревшая, заменена на get_db из db_manager
```

## Примечание
Все эти комментарии были удалены в рамках миграции на новую архитектуру БД с DBManager.
Старая архитектура использовала прямые вызовы AsyncPGPool, новая использует централизованный DBManager с репозиториями.