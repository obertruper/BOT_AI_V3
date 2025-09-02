# Система конфигурации BOT_AI_V3 v3.0

## 📋 Обзор

Новая система конфигурации BOT_AI_V3 построена на современных принципах с использованием Pydantic для валидации и типизации. Она обеспечивает надежность, безопасность и удобство работы с параметрами системы.

## ✨ Ключевые возможности

### 1. **Строгая типизация и валидация**

- Все параметры проверяются при загрузке через Pydantic модели
- Ранее обнаружение ошибок конфигурации
- IDE автокомплит и подсказки типов

### 2. **Профили окружений**

- Поддержка dev/staging/production профилей
- Наследование и переопределение параметров
- Легкое переключение между окружениями

### 3. **Безопасное управление секретами**

- Отделение секретов от конфигурации
- Поддержка .env файлов
- Маскирование в логах
- Опциональное шифрование

### 4. **Модульная архитектура**

- Логическое разделение по доменам
- Легкая навигация и поддержка
- Возможность частичной загрузки

## 🚀 Быстрый старт

### Базовое использование

```python
from core.config.loader import ConfigLoader
from core.config.models import RootConfig

# Загрузка конфигурации
loader = ConfigLoader()
config: RootConfig = loader.load(profile="development")

# Типизированный доступ к параметрам
print(f"Leverage: {config.trading.orders.default_leverage}x")
print(f"Database port: {config.database.port}")
print(f"ML enabled: {config.ml.enabled}")

# Валидация конфигурации
warnings = config.validate_consistency()
if warnings:
    print("Предупреждения:", warnings)
```

### Работа с секретами

```python
from core.config.secrets import get_secret, set_secret

# Получение секрета
api_key = get_secret("BYBIT_API_KEY", required=True)

# Установка секрета
set_secret("TELEGRAM_BOT_TOKEN", "your-token-here")

# Проверка всех обязательных секретов
from core.config.secrets import get_secrets_manager
manager = get_secrets_manager()
validation = manager.validate_required()
```

### Использование через старый API (обратная совместимость)

```python
from core.config.config_manager import get_global_config_manager

# Работает как раньше
config_manager = get_global_config_manager()
leverage = config_manager.get_config("trading.orders.default_leverage", 5)
```

## 📁 Структура конфигурационных файлов

```
config/
├── system.yaml          # Системные параметры
├── trading.yaml         # Торговые настройки
├── risk_management.yaml # Управление рисками
├── ml/
│   └── ml_config.yaml  # ML параметры
├── traders/            # Конфигурации трейдеров
│   └── *.yaml
└── .env               # Секреты (не в git!)
```

## 🔒 Управление секретами

### Создание .env файла

```bash
# .env
BYBIT_API_KEY=your-api-key-here
BYBIT_API_SECRET=your-api-secret-here
DB_PASSWORD=your-db-password
TELEGRAM_BOT_TOKEN=your-bot-token
```

### Экспорт шаблона

```python
from core.config.secrets import get_secrets_manager

manager = get_secrets_manager()
manager.export_template(Path(".env.template"))
```

## 🎯 Валидационные правила

### Критические проверки

- **PostgreSQL порт**: ДОЛЖЕН быть 5555
- **Leverage**: Рекомендуется 5x для production
- **Минимальная уверенность ML**: 0.35-0.70

### Автоматические проверки при запуске

1. Наличие обязательных параметров
2. Корректность типов данных
3. Диапазоны значений
4. Консистентность между секциями

## 🔄 Миграция со старой системы

См. [MIGRATION_FROM_V2.md](MIGRATION_FROM_V2.md) для пошагового руководства.

## 📊 Схема конфигурации

Полное описание всех параметров: [PYDANTIC_MODELS.md](PYDANTIC_MODELS.md)

## 🛠️ Расширенные возможности

### Hot-reload конфигурации

```python
from core.config.loader import ConfigLoader

loader = ConfigLoader()

def on_config_change(new_config):
    print("Конфигурация обновлена!")
    # Применить новые настройки

# Отслеживание изменений
observer = loader.watch_changes(on_config_change)
```

### Переменные окружения

Переопределение через переменные окружения:

```bash
export APP_TRADING__ORDERS__DEFAULT_LEVERAGE=10
export APP_DATABASE__PORT=5432
```

### Экспорт конфигурации

```python
# Экспорт для отладки (с маскированными секретами)
loader.export_config(Path("config_dump.yaml"), safe_mode=True)

# Полный экспорт (осторожно!)
loader.export_config(Path("config_full.yaml"), safe_mode=False)
```

## ⚠️ Важные замечания

1. **НЕ коммитьте .env файлы** в git
2. **Всегда используйте порт 5555** для PostgreSQL
3. **Проверяйте валидационный отчет** при запуске
4. **Используйте правильный профиль** для окружения

## 📚 Дополнительная документация

- [Примеры использования](examples/)
- [Управление секретами](SECRETS_MANAGEMENT.md)
- [Работа с профилями](PROFILES.md)
- [API Reference](../index.md)

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте валидационный отчет
2. Убедитесь в наличии всех секретов
3. Проверьте правильность профиля
4. См. [Troubleshooting](../../index.md)
