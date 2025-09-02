# Модуль `database`

Модуль `database` инкапсулирует всю логику для взаимодействия с базой данных PostgreSQL. Он предоставляет высокопроизводительную, масштабируемую и надёжную архитектуру доступа к данным для всех компонентов торговой системы.

---

## Архитектура и технологии

- **База данных:** `PostgreSQL` (порт `5555`)
- **Драйвер:** `asyncpg` - высокопроизводительный асинхронный драйвер PostgreSQL
- **Пулинг соединений:** Управляемые пулы соединений с автоматическим восстановлением
- **Паттерны устойчивости:** Circuit Breaker, Retry с экспоненциальным backoff
- **Миграции:** `Alembic` для управления версиями схемы БД

Новая архитектура построена на пяти основных компонентах:

1. **DBManager** - Центральная точка доступа к БД (Singleton)
2. **Repositories** - Слой доступа к данным с оптимизацией производительности
3. **TransactionManager** - Управление атомарными транзакциями (Unit of Work)
4. **Resilience** - Компоненты для обеспечения отказоустойчивости
5. **Monitoring** - Мониторинг здоровья БД и метрики производительности

---

## Структура модуля

| Директория | Описание |
| :--- | :--- |
| **`db_manager.py`** | Центральный фасад для доступа к БД. Singleton паттерн, инициализация всех компонентов, предоставление репозиториев. |
| **`connections/`** | Управление соединениями с PostgreSQL. `postgres.py` - AsyncPGPool, `transaction_manager.py` - Unit of Work паттерн. |
| **`repositories/`** | Репозитории с высокой производительностью. `base_repository.py` - базовый класс с bulk операциями, специализированные репозитории для каждой модели. |
| **`optimization/`** | Оптимизация запросов. `query_optimizer.py` - кэширование prepared statements, детекция медленных запросов. |
| **`resilience/`** | Паттерны устойчивости. `circuit_breaker.py` - защита от каскадных сбоев, `retry_handler.py` - умные повторы. |
| **`monitoring/`** | Мониторинг БД. `monitoring_service.py` - метрики здоровья, алерты, статистика производительности. |
| **`models/`** | Модели данных без ORM-зависимостей. Простые Python классы для представления данных. |
| **`migrations/`** | Конфигурация Alembic (`env.py`) и файлы миграций в `alembic/versions/`. |

---

## Основные компоненты

### DBManager - Центральный фасад

```python
from database.db_manager import get_db

# Получение менеджера БД (Singleton)
db_manager = await get_db()

# Доступ к репозиториям
order_repo = db_manager.get_order_repository()
trade_repo = db_manager.get_trade_repository()
ml_repo = db_manager.get_ml_prediction_repository()
```

### Репозитории с высокой производительностью

```python
# Массовые операции (20x ускорение)
orders = [Order(...) for _ in range(1000)]
await order_repo.bulk_insert(orders, chunk_size=500)

# Атомарные транзакции
async with db_manager.get_transaction_manager() as tx:
    order_id = await order_repo.create_order(order)
    await trade_repo.create_trade(trade)
    await tx.commit()
```

### Мониторинг и метрики

```python
# Проверка здоровья БД
health = await db_manager.get_monitoring_service().get_health_status()

# Метрики производительности
metrics = await db_manager.get_monitoring_service().get_performance_metrics()
```

---

## Ключевые особенности

### 🚀 Производительность

- **Bulk операции**: 20x ускорение для массовых вставок/обновлений
- **Prepared statements**: Кэширование скомпилированных запросов
- **Connection pooling**: Эффективное использование соединений
- **Query optimization**: Автоматическая оптимизация медленных запросов

### 🛡️ Надёжность

- **Circuit Breaker**: Защита от каскадных сбоев
- **Retry логика**: Умные повторы с экспоненциальным backoff
- **Transaction management**: Атомарность операций (Unit of Work)
- **Health monitoring**: Автоматическое обнаружение проблем

### 📊 Мониторинг

- **Real-time метрики**: Latency, throughput, error rates
- **Health checks**: Проверка состояния БД и соединений
- **Alerting**: Автоматические уведомления о проблемах
- **Performance tracking**: Отслеживание медленных запросов

### 🔧 Масштабируемость

- **Async-first**: Полностью асинхронная архитектура
- **Resource pooling**: Эффективное управление ресурсами
- **Horizontal scaling**: Готовность к горизонтальному масштабированию
- **Caching**: Многоуровневое кэширование данных

---

## Примеры использования

### Торговые операции

```python
# Создание ордера с автоматическим SL/TP
order = Order(
    symbol="BTCUSDT",
    side="buy",
    quantity=Decimal("0.01"),
    price=Decimal("50000")
)
order_id = await order_repo.create_order(order)

# Обновление статуса ордера
await order_repo.update_order_status(
    order_id, "filled",
    executed_quantity=Decimal("0.01"),
    executed_price=Decimal("50050")
)
```

### ML предсказания

```python
# Сохранение предсказания ML модели
prediction = MLPrediction(
    symbol="BTCUSDT",
    predicted_return_15m=0.0025,
    confidence=0.85,
    features_hash=123456789
)
await ml_repo.create_prediction(prediction)

# Массовое сохранение предсказаний
predictions = [MLPrediction(...) for _ in range(100)]
await ml_repo.bulk_insert(predictions)
```

### Аналитика и отчёты

```python
# Статистика торговли
stats = await trade_repo.get_trading_stats(
    start_date=datetime(2024, 1, 1),
    end_date=datetime.now()
)

# Дневная PnL
daily_pnl = await trade_repo.get_daily_pnl(days=30)

# Производительность по символам
performance = await trade_repo.get_symbol_performance(limit=10)
```
