# Agents - Система автоматических агентов BOT_AI_V3

## TestingAgent - Автоматическое тестирование и исправление ошибок

### Описание

TestingAgent - это интеллектуальный агент для автоматического тестирования, диагностики и исправления ошибок в системе BOT_AI_V3. Агент работает в режиме реального времени и может автоматически исправлять большинство распространенных проблем.

### Основные функции

#### 🔧 Автоматическое исправление ошибок

- **Конфликты портов** - автоматически освобождает занятые порты (8080, 5173, и др.)
- **Ошибки импорта** - устанавливает недостающие Python модули
- **Проблемы подключений** - проверяет и восстанавливает соединения с PostgreSQL, Redis
- **Ошибки базы данных** - создает БД, применяет миграции
- **ML ошибки** - проверяет наличие моделей, CUDA, PyTorch
- **Права доступа** - исправляет permissions для директорий и файлов

#### 📊 Диагностика системы

- **Анализ логов** - распознает 6 типов ошибок по regex паттернам
- **Мониторинг процессов** - отслеживает состояние компонентов системы
- **Системные метрики** - CPU, память, диск, uptime
- **Health checks** - проверка готовности всех сервисов

#### 🤖 Интеграция с агентами

- **debug-specialist** - для сложных ошибок
- **exchange-specialist** - для проблем с биржами
- **database-architect** - для оптимизации БД
- **ml-optimizer** - для ML проблем
- **performance-tuner** - для производительности

### Использование

#### 1. Через start_all.sh (рекомендуется)

```bash
./start_all.sh
# Выбрать пункт 11: 🤖 Запуск с автоматическим тестированием
```

Доступные режимы:

1. **Автоматическое тестирование + Полная система** - мониторинг всех компонентов
2. **Автоматическое тестирование + Core система** - только торговый движок
3. **Автоматическое тестирование + API система** - только API сервер
4. **Только диагностика и исправление ошибок** - разовая проверка
5. **Проверить занятые порты и освободить их** - исправление конфликтов портов

#### 2. Прямой запуск

```bash
# Активация venv
source venv/bin/activate

# Диагностика системы
python test_testing_agent.py --action=diagnosis

# Исправление портов
python test_testing_agent.py --action=ports

# Анализ логов
python test_testing_agent.py --action=logs

# Мониторинг системы
python test_testing_agent.py --action=monitor
```

#### 3. Программное использование

```python
import asyncio
from agents.testing_agent import TestingAgent

async def main():
    agent = TestingAgent()

    # Исправление конфликтов портов
    await agent.fix_port_conflicts()

    # Анализ ошибок в логах
    errors = await agent.analyze_errors(log_content)

    # Запуск системы с мониторингом
    await agent.start_system_monitoring("full")

    # Получение отчета
    report = agent.get_error_report()

asyncio.run(main())
```

### Типы обнаруживаемых ошибок

#### 1. Port Occupied (port_occupied)

```
Address already in use
port 8080 is already in use
Error: listen EADDRINUSE
```

**Исправление**: Автоматическое завершение процессов на занятых портах

#### 2. Import Errors (import_error)

```
ModuleNotFoundError: No module named 'passlib'
ImportError: cannot import name 'something'
```

**Исправление**: Автоматическая установка недостающих модулей через pip

#### 3. Connection Errors (connection_error)

```
connection refused
Could not connect to Redis
Database connection failed
```

**Исправление**: Проверка и восстановление соединений

#### 4. Database Errors (database_error)

```
database "bot_trading_v3" does not exist
relation "orders" does not exist
FATAL: database error
```

**Исправление**: Создание БД, применение миграций

#### 5. ML Errors (ml_error)

```
No module named 'torch'
CUDA not available
Model file not found
```

**Исправление**: Установка PyTorch, проверка моделей

#### 6. Permission Errors (permission_error)

```
Permission denied
PermissionError: [Errno 13]
Access denied
```

**Исправление**: Исправление прав доступа к файлам и директориям

### Логирование

TestingAgent создает подробные логи:

```
/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/data/logs/testing_agent.log
```

Структура логов:

- `INFO` - общая информация о работе
- `WARNING` - обнаруженные ошибки
- `ERROR` - критические проблемы
- `DEBUG` - детальная отладочная информация

### Конфигурация

TestingAgent настраивается через параметры конструктора:

```python
agent = TestingAgent(
    project_root="/path/to/BOT_AI_V3",  # Корень проекта
    # Автоматически определяются:
    # venv_python = project_root/venv/bin/python
    # logs_dir = project_root/data/logs
)
```

### Интеграция с системой

TestingAgent интегрируется с:

1. **UnifiedLauncher** - может запускать систему под своим контролем
2. **ProcessManager** - мониторит процессы системы
3. **HealthMonitor** - использует health checks
4. **AI Agent System** - вызывает специализированных агентов
5. **MCP серверы** - использует filesystem, postgres, sequential-thinking

### Примеры использования

#### Исправление проблемы с портом 8080

```bash
# Быстрое исправление
python test_testing_agent.py --action=ports

# Через start_all.sh
./start_all.sh
# Выбрать: 11 → 5 (Проверить занятые порты)
```

#### Полная диагностика перед запуском

```bash
python test_testing_agent.py --action=diagnosis
```

#### Мониторинг работающей системы

```bash
# Запуск системы под контролем TestingAgent
./start_all.sh
# Выбрать: 11 → 1 (Полная система с тестированием)
```

### Метрики и отчеты

TestingAgent предоставляет детальные отчеты:

```python
report = agent.get_error_report()
# {
#   'total_errors': 50,
#   'error_types': {
#     'port_occupied': 49,
#     'database_error': 1
#   },
#   'recent_errors': [...],
#   'timestamp': '2025-08-04T12:28:00'
# }
```

### Troubleshooting

#### TestingAgent не запускается

```bash
# Проверьте наличие файла
ls -la agents/testing_agent.py

# Проверьте виртуальное окружение
source venv/bin/activate
python -c "import psutil; print('OK')"
```

#### Не исправляются ошибки портов

```bash
# Проверьте права пользователя
sudo lsof -i :8080

# Запустите с правами администратора
sudo python test_testing_agent.py --action=ports
```

#### Агент не находит логи

```bash
# Создайте директорию логов
mkdir -p data/logs

# Проверьте права доступа
chmod 755 data/logs
```

### Разработка и расширение

TestingAgent легко расширяется новыми типами ошибок:

```python
# Добавить новый паттерн ошибки
class ErrorPattern:
    NEW_ERROR_TYPE = [
        r"your regex pattern here",
        r"another pattern"
    ]

# Добавить обработчик
async def fix_new_error_type(self, error_info: Dict):
    # Логика исправления
    pass

# Зарегистрировать в analyze_errors
error_types['new_error_type'] = ErrorPattern.NEW_ERROR_TYPE
```

## Архитектура

```
TestingAgent
├── ErrorPattern (класс паттернов ошибок)
├── fix_* методы (исправление ошибок)
├── analyze_errors (анализ логов)
├── start_system_monitoring (мониторинг)
├── call_specialized_agent (интеграция с агентами)
└── get_error_report (отчеты)
```

## Зависимости

- **Python 3.8+**
- **asyncio** - асинхронное выполнение
- **psutil** - системная информация
- **pathlib** - работа с путями
- **re** - регулярные выражения
- **subprocess** - управление процессами
- **logging** - логирование

## Версия

- **Версия**: 1.0.0
- **Автор**: Claude Code Agent System
- **Дата**: 4 августа 2025
- **Статус**: Готов к продакшену

---

TestingAgent - это мощный инструмент для обеспечения стабильности и надежности BOT_AI_V3. Используйте его для автоматического решения проблем и поддержания системы в рабочем состоянии.
