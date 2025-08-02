# Health Check Implementation для BOT Trading v3

## Обзор

Реализована комплексная система проверки здоровья для BOT Trading v3, которая мониторит все критические компоненты системы.

## Компоненты проверки

### 1. База данных PostgreSQL

- Проверка подключения с таймаутом
- Измерение времени отклика
- Мониторинг активных подключений
- Проверка размера БД

### 2. Redis кеш

- Проверка доступности
- Тест операций SET/GET
- Мониторинг использования памяти
- Измерение латентности

### 3. Подключения к биржам

- Проверка доступности каждой биржи
- Измерение латентности API
- Обработка rate limit ошибок
- Агрегированный статус всех бирж

### 4. Системные ресурсы

- CPU использование (порог: 85%)
- RAM использование (порог: 90%)
- Дисковое пространство (порог: 95%)
- Сетевые подключения

### 5. Внутренние компоненты

- Trader Manager
- Strategy Manager
- Exchange Registry

## API Endpoints

### 1. Основной health check endpoint

```
GET /api/health
```

Возвращает:

```json
{
  "status": "healthy|warning|critical|degraded|error",
  "timestamp": "2025-01-29T12:00:00.000Z",
  "uptime_seconds": 3600,
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "exchanges": "warning",
    "system_resources": "healthy",
    "traders": "healthy",
    "strategies": "unknown"
  },
  "basic_components": {
    "orchestrator": true,
    "trader_manager": true,
    "exchange_factory": true,
    "config_manager": true,
    "web_bridge": true
  },
  "details": {
    "system": {
      "cpu": {
        "percent": 45.2,
        "cores": 8,
        "frequency_mhz": 2400
      },
      "memory": {
        "total_gb": 16.0,
        "available_gb": 8.5,
        "percent": 46.9
      },
      "disk": {
        "total_gb": 500.0,
        "free_gb": 150.0,
        "percent": 70.0
      }
    }
  }
}
```

### 2. Monitoring health endpoint

```
GET /api/monitoring/health
```

Возвращает детализированную информацию о здоровье системы с историей проверок.

### 3. System metrics endpoint

```
GET /api/monitoring/metrics
```

Возвращает текущие метрики производительности системы.

## Архитектура

### HealthChecker класс (`core/system/health_checker.py`)

Основной компонент, отвечающий за:

- Параллельную проверку всех компонентов
- Кеширование результатов (TTL: 30 секунд)
- Агрегирование статусов
- Детальные отчеты

### Интеграция с SystemOrchestrator

HealthChecker инициализируется в SystemOrchestrator и имеет доступ ко всем критическим компонентам системы.

## Статусы компонентов

- **healthy** - компонент работает нормально
- **warning** - есть некритические проблемы
- **critical** - критические проблемы, требующие вмешательства
- **unknown** - статус неизвестен (компонент не инициализирован)

## Использование

### 1. Через API

```bash
curl http://localhost:8080/api/health
```

### 2. Программно

```python
from core.system.health_checker import HealthChecker

health_checker = HealthChecker(config_manager)
results = await health_checker.check_all_components()
detailed_report = await health_checker.get_detailed_report()
```

### 3. Демонстрационный скрипт

```bash
python scripts/demo_health_check.py
```

## Конфигурация

В `config.yaml`:

```yaml
health_check:
  db_timeout: 5.0        # Таймаут для проверки БД (секунды)
  redis_timeout: 3.0     # Таймаут для проверки Redis
  exchange_timeout: 10.0 # Таймаут для проверки бирж
  cache_ttl: 30         # Время жизни кеша результатов
  cpu_threshold: 85.0    # Порог CPU для warning
  memory_threshold: 90.0 # Порог памяти для warning
  disk_threshold: 95.0   # Порог диска для warning
```

## Тестирование

### Unit тесты

```bash
pytest tests/test_health_check.py::test_health_checker_unit
```

### Интеграционные тесты

```bash
# Запустите веб-сервер
python web/launcher.py

# В другом терминале
pytest tests/test_health_check.py
```

## Мониторинг и алерты

Health check интегрирован с системой мониторинга:

- Автоматические проверки каждые 30 секунд
- Логирование проблем через structlog
- Метрики в Prometheus формате
- Возможность настройки алертов

## Производительность

- Все проверки выполняются параллельно
- Кеширование результатов снижает нагрузку
- Таймауты предотвращают зависание
- Graceful обработка ошибок

## Расширение

Для добавления новых проверок:

1. Добавьте метод в HealthChecker:

```python
async def check_new_component(self) -> str:
    """Проверка нового компонента"""
    # Логика проверки
    return "healthy"  # или "warning", "critical"
```

2. Добавьте вызов в `check_all_components()`:

```python
checks = [
    # ...
    ("new_component", self.check_new_component()),
]
```

## Troubleshooting

### "Database critical"

- Проверьте запущен ли PostgreSQL
- Проверьте конфигурацию подключения
- Проверьте сетевую доступность

### "Redis critical"

- Проверьте запущен ли Redis
- Проверьте пароль и порт
- Проверьте память системы

### "Exchanges warning/critical"

- Проверьте API ключи
- Проверьте интернет-соединение
- Проверьте rate limits
