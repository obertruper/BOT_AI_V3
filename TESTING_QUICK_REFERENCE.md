# 🚀 Быстрый справочник по тестированию BOT_AI_V3

## ⚡ Самые важные команды (копировать и запускать)

### 🎯 Быстрый старт
```bash
# 1. ВСЕГДА активировать venv первым!
source venv/bin/activate

# 2. Запустить все тесты с покрытием
pytest --cov=. --cov-report=html

# 3. Открыть отчет покрытия
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### 📊 Текущий статус
- **Покрытие**: 8% ✅
- **Тестов**: 80+ ✅
- **Цель**: 90%+ 🎯

## 🔥 Основные команды тестирования

```bash
# === БАЗОВЫЕ КОМАНДЫ ===

# Запустить ВСЕ тесты
pytest

# Запустить с подробностями
pytest -v

# Запустить конкретный файл
pytest tests/unit/test_basic_functionality.py

# Запустить только unit тесты
pytest tests/unit/

# Запустить только integration тесты
pytest tests/integration/

# === ПОКРЫТИЕ КОДА ===

# HTML отчет (РЕКОМЕНДУЕТСЯ)
pytest --cov=. --cov-report=html

# Отчет в терминале с пропущенными строками
pytest --cov=. --cov-report=term-missing

# Проверить покрытие конкретного модуля
pytest --cov=trading tests/

# === ОТЛАДКА ===

# Показать print() выводы
pytest -s

# Остановиться на первой ошибке
pytest -x

# Запустить только упавшие тесты
pytest --lf

# Показать 10 самых медленных тестов
pytest --durations=10

# === ПАРАЛЛЕЛЬНЫЙ ЗАПУСК ===

# Установить (один раз)
pip install pytest-xdist

# Запустить на всех ядрах
pytest -n auto

# === ФИЛЬТРАЦИЯ ТЕСТОВ ===

# По имени
pytest -k "test_import"

# По маркерам
pytest -m "not slow"
pytest -m integration
pytest -m requires_db
```

## 📁 Структура тестов (где что лежит)

```
tests/
├── unit/                              # Быстрые тесты без внешних зависимостей
│   ├── test_basic_functionality.py   ⭐ # Основные импорты и базовые функции
│   ├── test_imports_only.py         ⭐ # Проверка всех импортов
│   ├── test_system_components.py    ⭐ # Системные компоненты
│   └── test_utilities_and_indicators.py ⭐ # Утилиты и индикаторы
├── integration/                       # Тесты интеграции компонентов
└── performance/                       # Тесты производительности
```

## 🛠️ Unified Test Runner (продвинутое тестирование)

```bash
# Полный анализ (тесты + покрытие + отчеты)
python3 scripts/unified_test_runner.py --mode=full

# Только тесты
python3 scripts/unified_test_runner.py --mode=tests

# Только покрытие
python3 scripts/unified_test_runner.py --mode=coverage
```

## ✅ Проверка перед коммитом

```bash
# Скопировать и выполнить ВСЕ команды:
source venv/bin/activate
black . && ruff check --fix .
pytest tests/unit/ --cov=. --cov-report=term-missing
git diff --staged | grep -i "api_key\|secret\|password"
```

## 🆘 Решение частых проблем

### ❌ ImportError
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ PostgreSQL connection failed
```bash
# ВАЖНО: Порт 5555, НЕ 5432!
psql -p 5555 -U obertruper -d bot_trading_v3
```

### ❌ Async test not running
```bash
pip install pytest-asyncio
```

### ❌ Coverage не работает
```bash
pip install --upgrade pytest-cov
rm -rf .pytest_cache htmlcov .coverage
```

## 📈 Как увеличить покрытие?

### Приоритетные файлы для тестирования:
1. `trading/engine.py` - Торговый движок (критично!)
2. `ml/ml_manager.py` - ML система
3. `trading/orders/order_manager.py` - Управление ордерами
4. `risk_management/manager.py` - Управление рисками
5. `exchanges/bybit/client.py` - Интеграция с биржей

### Шаблон нового теста (копировать и адаптировать):

```python
"""Тесты для модуля XXX"""

import pytest
from unittest.mock import Mock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestMyModule:
    """Тесты для MyModule"""
    
    def test_basic_import(self):
        """Тест импорта"""
        from my.module import MyClass
        assert MyClass is not None
    
    def test_basic_functionality(self):
        """Тест базовой функции"""
        from my.module import my_function
        result = my_function(1, 2)
        assert result == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## 📊 Метрики для отслеживания

| Метрика | Текущее | Цель | Статус |
|---------|---------|------|--------|
| Общее покрытие | 8% | 90% | 🔴 |
| Unit тесты | 80+ | 500+ | 🟡 |
| Integration тесты | 3 | 50+ | 🔴 |
| Performance тесты | 4 | 20+ | 🔴 |
| Время выполнения | <10s | <30s | 🟢 |

## 🎯 Что делать дальше?

1. **Запустить тесты сейчас:**
   ```bash
   source venv/bin/activate
   pytest --cov=. --cov-report=html
   ```

2. **Посмотреть покрытие:**
   - Открыть `htmlcov/index.html`
   - Найти файлы с 0% покрытия
   - Создать тесты для них

3. **Добавить новый тест:**
   - Скопировать шаблон выше
   - Создать файл в `tests/unit/test_ваш_модуль.py`
   - Запустить: `pytest tests/unit/test_ваш_модуль.py -v`

---

💡 **Совет**: Начните с простых импорт-тестов - они быстро увеличивают покрытие!

📚 **Полная документация**: `docs/TESTING_DOCUMENTATION.md`

⏱️ **Обновлено**: 17 августа 2025