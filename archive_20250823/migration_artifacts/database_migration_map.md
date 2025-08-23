# Карта миграции импортов БД - 23 августа 2025

## Основные изменения импортов

### 1. Репозитории

**Было:**
```python
from database.repositories.signal_repository_fixed import SignalRepositoryFixed
from database.connections import get_async_db
```

**Стало:**
```python
from database.repositories.signal_repository import SignalRepository
from database.db_manager import get_db
```

### 2. Прямые обращения к пулу

**Было:**
```python
from database.connections.postgres import AsyncPGPool

# Использование
await AsyncPGPool.fetch(query)
await AsyncPGPool.execute(query, *params)
```

**Стало:**
```python
from database.db_manager import get_db

# Использование
db_manager = await get_db()
repo = db_manager.get_order_repository()
await repo.create_order(order)
```

### 3. Создание репозиториев

**Было:**
```python
async with get_async_db() as db:
    signal_repo = SignalRepository(db)
    await signal_repo.save_signal(signal)
```

**Стало:**
```python
db_manager = await get_db()
signal_repo = db_manager.get_signal_repository()
await signal_repo.save_signal(signal)
```

## Обновлённые файлы

### Критические (обновлены):
1. ✅ trading/engine.py
2. ✅ ml/ml_prediction_logger.py
3. ✅ web/api/endpoints/testing.py
4. ✅ trading/position_tracker.py
5. ✅ database/connections/__init__.py

### Вторичные (требуют обновления):
- core/system/process_monitor.py
- ml/ml_signal_processor.py
- data/data_loader.py
- monitoring/telegram/bot.py

## Новые возможности

### DBManager предоставляет:
- **Централизованный доступ** - Singleton паттерн
- **Bulk операции** - 20x ускорение для массовых вставок
- **Транзакции** - Unit of Work паттерн
- **Мониторинг** - Real-time метрики и health checks
- **Устойчивость** - Circuit Breaker и Retry логика

### Пример использования:
```python
from database.db_manager import get_db

# Получение менеджера БД
db_manager = await get_db()

# Работа с репозиториями
order_repo = db_manager.get_order_repository()
trade_repo = db_manager.get_trade_repository()
ml_repo = db_manager.get_ml_prediction_repository()

# Атомарная транзакция
async with db_manager.get_transaction_manager() as tx:
    order_id = await order_repo.create_order(order)
    await trade_repo.create_trade(trade)
    await tx.commit()

# Массовые операции
orders = [Order(...) for _ in range(1000)]
await order_repo.bulk_insert(orders, chunk_size=500)
```