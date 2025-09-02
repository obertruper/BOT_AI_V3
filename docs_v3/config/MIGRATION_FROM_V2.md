# Руководство по миграции на систему конфигурации v3

## 📋 Обзор изменений

### Что изменилось

- ✅ **Типизация**: Все параметры теперь типизированы через Pydantic
- ✅ **Валидация**: Проверка при загрузке, а не в runtime
- ✅ **Секреты**: Отделены от основной конфигурации
- ✅ **Профили**: Поддержка dev/staging/prod окружений
- ✅ **API**: Новые типизированные методы доступа

### Обратная совместимость

Старый код продолжит работать благодаря адаптеру. Миграция может быть постепенной.

## 🚀 Этапы миграции

### Этап 1: Подготовка (без изменения кода)

#### 1.1 Установка зависимостей

```bash
pip install pydantic python-dotenv cryptography
```

#### 1.2 Создание .env файла

```bash
# Скопируйте шаблон
cp .env.example .env

# Добавьте ваши секреты
nano .env
```

#### 1.3 Проверка совместимости

```python
# test_compatibility.py
from core.config.config_manager import ConfigManager
from core.config.loader import ConfigLoader

# Старый способ должен работать
old_cm = ConfigManager()
print("Old API:", old_cm.get_config("trading.orders.default_leverage"))

# Новый способ
loader = ConfigLoader()
config = loader.load()
print("New API:", config.trading.orders.default_leverage)
```

### Этап 2: Постепенная миграция компонентов

#### 2.1 Миграция простого компонента

**Было:**

```python
# trading/some_component.py
from core.config.config_manager import get_global_config_manager

class SomeComponent:
    def __init__(self):
        self.config_manager = get_global_config_manager()

    def get_leverage(self):
        return self.config_manager.get_config("trading.orders.default_leverage", 5)
```

**Стало:**

```python
# trading/some_component.py
from core.config.loader import ConfigLoader
from core.config.models import TradingSettings

class SomeComponent:
    def __init__(self):
        loader = ConfigLoader()
        self.config = loader.load()

    def get_leverage(self) -> int:
        # Типизированный доступ
        return self.config.trading.orders.default_leverage
```

#### 2.2 Миграция с использованием адаптера

Для сложных компонентов используйте адаптер:

```python
# core/config/adapter.py уже создан
from core.config.adapter import ConfigAdapter

class ComplexComponent:
    def __init__(self):
        # Адаптер обеспечивает совместимость
        self.config = ConfigAdapter()

    def old_method(self):
        # Старый API продолжает работать
        return self.config.get_config("some.nested.key")
```

### Этап 3: Миграция критических компонентов

#### 3.1 Trading Engine

```python
# trading/engine.py
from core.config.models import TradingSettings, RiskManagementSettings

class TradingEngine:
    def __init__(self, config: RootConfig):
        self.trading_config: TradingSettings = config.trading
        self.risk_config: RiskManagementSettings = config.risk_management

        # Типизированный доступ
        self.leverage = self.trading_config.orders.default_leverage
        self.max_positions = self.risk_config.global_risk.max_open_positions
```

#### 3.2 Risk Manager

```python
# risk_management/manager.py
from core.config.models import RiskManagementSettings

class RiskManager:
    def __init__(self, risk_config: RiskManagementSettings):
        self.config = risk_config

        # Все параметры валидированы
        self.stop_loss = self.config.position.default_stop_loss
        self.take_profit = self.config.position.default_take_profit
```

### Этап 4: Удаление старого кода

После полной миграции:

1. Удалите импорты старого ConfigManager где возможно
2. Замените словари на типизированные модели
3. Удалите ручные проверки валидации

## 📝 Чеклист миграции

### Для каждого компонента

- [ ] Идентифицировать использование ConfigManager
- [ ] Определить необходимые параметры конфигурации
- [ ] Выбрать стратегию миграции (прямая/через адаптер)
- [ ] Обновить импорты
- [ ] Добавить типы для параметров
- [ ] Протестировать компонент
- [ ] Удалить старый код (опционально)

## 🔧 Типичные сценарии миграции

### Сценарий 1: Простое чтение параметра

**Было:**

```python
leverage = config_manager.get_config("trading.leverage", 5)
```

**Стало:**

```python
leverage = config.trading.orders.default_leverage
```

### Сценарий 2: Динамическое чтение

**Было:**

```python
def get_param(key: str):
    return config_manager.get_config(key)
```

**Стало (с адаптером):**

```python
def get_param(key: str):
    return adapter.get_config(key)  # Совместимость
```

### Сценарий 3: Проверка наличия

**Было:**

```python
if config_manager.get_config("ml.enabled"):
    # ML логика
```

**Стало:**

```python
if config.ml.enabled:
    # ML логика (с гарантией типа bool)
```

## ⚠️ Частые проблемы и решения

### Проблема: ImportError для ConfigurationError

**Решение:** Убедитесь, что ConfigurationError добавлен в core/exceptions.py

### Проблема: Отсутствующие секреты

**Решение:**

```python
from core.config.secrets import get_secrets_manager

manager = get_secrets_manager()
print(manager.get_status_report())  # Покажет отсутствующие секреты
```

### Проблема: Несоответствие типов

**Решение:** Используйте правильные типы из models.py:

```python
from core.config.models import TradingSettings

def process_trading(settings: TradingSettings):  # Явный тип
    ...
```

## 📊 Примеры миграции реальных компонентов

### Пример: OrderManager

```python
# До миграции
class OrderManager:
    def __init__(self):
        self.cm = get_global_config_manager()
        self.leverage = self.cm.get_config("trading.leverage")
        self.min_order = self.cm.get_config("trading.min_order_size")

# После миграции
class OrderManager:
    def __init__(self, trading_config: TradingSettings):
        self.leverage = trading_config.orders.default_leverage
        self.min_order = trading_config.orders.min_order_size
```

### Пример: MLManager

```python
# До миграции
class MLManager:
    def __init__(self):
        self.enabled = get_config("ml.enabled", False)
        self.model_path = get_config("ml.model.path")

# После миграции
class MLManager:
    def __init__(self, ml_config: MLSettings):
        self.enabled = ml_config.enabled
        self.model_path = ml_config.model.path
        # Бонус: path уже валидирован как Path объект!
```

## ✅ Преимущества после миграции

1. **IDE поддержка**: Автокомплит и проверка типов
2. **Ранняя валидация**: Ошибки при запуске, не в runtime
3. **Безопасность**: Секреты изолированы
4. **Производительность**: Кеширование и оптимизация
5. **Поддерживаемость**: Понятная структура и типы

## 🎯 Финальная проверка

После завершения миграции выполните:

```bash
# Запустите тесты
pytest tests/unit/config/

# Проверьте систему
python3 -c "from core.config.loader import ConfigLoader; l = ConfigLoader(); print(l.get_validation_report())"

# Запустите систему
./start_with_logs_filtered.sh
```

## 📚 Дополнительные ресурсы

- [Pydantic модели](PYDANTIC_MODELS.md)
- [Примеры кода](examples/)
- [API Reference](README.md)
