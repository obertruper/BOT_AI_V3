# 📚 Полная документация по тестированию BOT_AI_V3

## 📋 Оглавление
- [Обзор системы тестирования](#обзор-системы-тестирования)
- [Структура тестов](#структура-тестов)
- [Основные команды](#основные-команды)
- [Запуск тестов](#запуск-тестов)
- [Анализ покрытия](#анализ-покрытия)
- [Создание новых тестов](#создание-новых-тестов)
- [CI/CD интеграция](#cicd-интеграция)
- [Troubleshooting](#troubleshooting)

## 🎯 Обзор системы тестирования

### Текущее состояние
- **Покрытие кода**: 8% (базовая инфраструктура создана)
- **Количество тестов**: 80+ тестовых случаев
- **Фреймворки**: pytest, pytest-asyncio, pytest-cov
- **Цель**: Достижение 90%+ покрытия кода

### Используемые инструменты
```bash
# Основные пакеты тестирования
pytest==8.4.1          # Основной фреймворк
pytest-cov==6.2.1      # Измерение покрытия
pytest-asyncio==0.24.0 # Асинхронные тесты
pytest-mock==3.14.0    # Моки и патчи
black==24.8.0          # Форматирование кода
ruff==0.8.6           # Линтер
mypy==1.14.1          # Проверка типов
```

## 📁 Структура тестов

```
tests/
├── unit/                          # Unit тесты
│   ├── test_basic_functionality.py    # Базовая функциональность (26 тестов)
│   ├── test_imports_only.py          # Проверка импортов (24 теста)
│   ├── test_system_components.py     # Системные компоненты (30+ тестов)
│   ├── test_utilities_and_indicators.py # Утилиты и индикаторы (20+ тестов)
│   ├── core/                      # Тесты ядра
│   │   └── test_orchestrator_ml.py
│   ├── ml/                        # Тесты ML системы
│   │   ├── test_ml_manager.py
│   │   ├── test_ml_signal_processor.py
│   │   ├── test_feature_engineering.py
│   │   └── test_patchtst_model.py
│   ├── trading/                   # Тесты торговой системы
│   │   ├── test_engine.py
│   │   ├── test_order_executor.py
│   │   └── sltp/
│   │       └── test_enhanced_manager.py
│   ├── database/                  # Тесты БД
│   │   └── test_market_data_models.py
│   ├── exchanges/                 # Тесты бирж
│   ├── risk_management/          # Тесты управления рисками
│   └── strategies/               # Тесты стратегий
├── integration/                   # Интеграционные тесты
│   ├── test_complete_trading.py
│   ├── test_enhanced_logging.py
│   ├── test_enhanced_sltp.py
│   ├── test_database_api_integration.py
│   ├── test_exchange_trading_integration.py
│   ├── test_trading_ml_integration.py
│   └── test_websocket_realtime_integration.py
├── performance/                   # Тесты производительности
│   ├── test_api_response.py      # < 100ms response time
│   ├── test_ml_inference.py      # < 20ms inference
│   ├── test_database_queries.py  # Query optimization
│   └── test_trading_latency.py   # < 50ms trading operations
├── fixtures/                      # Фикстуры pytest
│   └── ml_fixtures.py
└── conftest.py                    # Глобальная конфигурация pytest
```

## 🚀 Основные команды

### Быстрый запуск тестов

```bash
# Активация виртуального окружения (ВСЕГДА ПЕРВЫМ!)
source venv/bin/activate

# Запуск всех тестов
pytest

# Запуск с подробным выводом
pytest -v

# Запуск с покрытием
pytest --cov=. --cov-report=html

# Запуск только unit тестов
pytest tests/unit/

# Запуск только integration тестов
pytest tests/integration/

# Запуск только performance тестов
pytest tests/performance/
```

### Запуск конкретных тестов

```bash
# Запуск одного файла
pytest tests/unit/test_basic_functionality.py

# Запуск конкретного теста
pytest tests/unit/test_basic_functionality.py::TestBasicImports::test_core_config_import

# Запуск тестов по паттерну имени
pytest -k "test_import"

# Запуск тестов с определенным маркером
pytest -m "not slow"        # Пропустить медленные тесты
pytest -m integration        # Только интеграционные
pytest -m requires_db        # Только с БД
```

### Параллельный запуск

```bash
# Установка плагина для параллельного запуска
pip install pytest-xdist

# Запуск на всех ядрах CPU
pytest -n auto

# Запуск на 4 ядрах
pytest -n 4
```

## 📊 Анализ покрытия

### Генерация отчетов покрытия

```bash
# HTML отчет (рекомендуется)
pytest --cov=. --cov-report=html
# Открыть: htmlcov/index.html

# Отчет в терминале
pytest --cov=. --cov-report=term

# Отчет с пропущенными строками
pytest --cov=. --cov-report=term-missing

# XML отчет для CI/CD
pytest --cov=. --cov-report=xml

# JSON отчет
pytest --cov=. --cov-report=json

# Множественные отчеты
pytest --cov=. --cov-report=html --cov-report=term
```

### Проверка покрытия конкретных модулей

```bash
# Покрытие только trading модуля
pytest --cov=trading tests/

# Покрытие ML системы
pytest --cov=ml tests/

# Покрытие с исключениями
pytest --cov=. --cov-report=html --cov-config=.coveragerc
```

### Настройка минимального покрытия

```bash
# Fail если покрытие меньше 80%
pytest --cov=. --cov-fail-under=80

# Для разработки (не fail)
pytest --cov=. --cov-fail-under=0
```

## 🔧 Специальные команды тестирования

### Unified Test Runner (Рекомендуется)

```bash
# Полный анализ и тестирование
python3 scripts/unified_test_runner.py --mode=full

# Только тесты
python3 scripts/unified_test_runner.py --mode=tests

# Только покрытие
python3 scripts/unified_test_runner.py --mode=coverage

# Enhanced анализ
python3 scripts/unified_test_runner.py --mode=enhanced
```

### Master Test Runner

```bash
# Полный анализ с генерацией тестов
python3 scripts/master_test_runner.py --full-analysis

# Анализ зависимостей
python3 scripts/code_chain_analyzer.py

# Тестирование цепочек выполнения
python3 scripts/full_chain_tester.py --chain=trading

# Мониторинг покрытия в реальном времени
python3 scripts/coverage_monitor.py --realtime
```

### Генерация тестов

```bash
# Массовая генерация тестов
python3 scripts/mass_test_generator.py

# Генерация бизнес-тестов
python3 scripts/generate_business_tests.py

# Умная генерация тестов
python3 scripts/smart_test_manager.py --generate

# Bash скрипт для генерации всех тестов
./scripts/generate_all_tests.sh
```

## 🧪 Создание новых тестов

### Шаблон Unit теста

```python
"""
Тесты для модуля XXX
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import os
import sys

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestModuleName:
    """Тесты для ModuleName"""
    
    def test_basic_functionality(self):
        """Тест базовой функциональности"""
        from module.submodule import ClassName
        
        obj = ClassName()
        assert obj is not None
        
    def test_with_mock(self):
        """Тест с использованием моков"""
        from module.submodule import function_to_test
        
        mock_dependency = Mock()
        mock_dependency.method.return_value = "expected"
        
        result = function_to_test(mock_dependency)
        assert result == "expected"
        
    @pytest.mark.asyncio
    async def test_async_function(self):
        """Тест асинхронной функции"""
        from module.async_module import async_function
        
        result = await async_function()
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Шаблон Integration теста

```python
"""
Интеграционные тесты для XXX
"""

import pytest
import asyncio
from datetime import datetime


@pytest.mark.integration
class TestIntegration:
    """Интеграционные тесты"""
    
    @pytest.fixture
    async def setup_environment(self):
        """Настройка тестового окружения"""
        # Setup
        yield
        # Teardown
        
    @pytest.mark.asyncio
    async def test_full_flow(self, setup_environment):
        """Тест полного workflow"""
        # Тест интеграции компонентов
        pass
```

## 🔍 Отладка тестов

### Команды отладки

```bash
# Показать print() выводы
pytest -s

# Остановиться на первой ошибке
pytest -x

# Показать локальные переменные при ошибке
pytest -l

# Запустить отладчик при ошибке
pytest --pdb

# Максимально подробный вывод
pytest -vvv

# Показать самые медленные тесты
pytest --durations=10

# Запустить только упавшие тесты
pytest --lf

# Запустить сначала упавшие тесты
pytest --ff
```

### Проверка перед коммитом

```bash
# Полная проверка кода
source venv/bin/activate
black . && ruff check --fix .
mypy . --ignore-missing-imports
pytest tests/unit/ --cov=. --cov-report=term-missing
git diff --staged | grep -i "api_key\|secret\|password"
```

## 📈 Мониторинг прогресса

### Текущие метрики
- **Общее покрытие**: 8%
- **Цель покрытия**: 90%+
- **Количество тестов**: 80+
- **Успешных тестов**: ~50

### Приоритеты для увеличения покрытия

1. **Trading Engine** (trading/engine.py) - критический компонент
2. **ML System** (ml/) - модели и обработка сигналов
3. **Order Management** (trading/orders/) - управление ордерами
4. **Risk Management** (risk_management/) - контроль рисков
5. **Exchange Integration** (exchanges/) - интеграция с биржами

## 🐛 Troubleshooting

### Частые проблемы и решения

#### ImportError при запуске тестов
```bash
# Решение: активировать venv
source venv/bin/activate
pip install -r requirements.txt
```

#### PostgreSQL connection failed
```bash
# Проверить что PostgreSQL на порту 5555!
psql -p 5555 -U obertruper -d bot_trading_v3
```

#### Async test not running
```bash
# Установить pytest-asyncio
pip install pytest-asyncio

# Добавить в pytest.ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

#### Coverage не работает
```bash
# Переустановить pytest-cov
pip install --upgrade pytest-cov

# Очистить кеш
rm -rf .pytest_cache
rm -rf htmlcov
rm .coverage
```

## 🚦 CI/CD интеграция

### GitHub Actions workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: bot_trading_v3
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5555:5432
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests with coverage
      run: |
        pytest --cov=. --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

## 📚 Дополнительные ресурсы

### Документация
- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)

### Внутренние документы
- `docs/TESTING_COMPLETE_GUIDE.md` - Полное руководство
- `docs/100_PERCENT_COVERAGE_PLAN.md` - План достижения 100% покрытия
- `docs/CODE_QUALITY.md` - Стандарты качества кода

## 🎯 Roadmap

### Phase 1 (Текущая) ✅
- [x] Создать базовую инфраструктуру тестирования
- [x] Достичь 8% покрытия
- [x] Настроить CI/CD

### Phase 2 (В процессе)
- [ ] Достичь 30% покрытия
- [ ] Полное покрытие критических компонентов
- [ ] Интеграционные тесты для всех workflow

### Phase 3 (Планируется)
- [ ] Достичь 60% покрытия
- [ ] Performance тесты для всех endpoints
- [ ] E2E тесты с реальными биржами (testnet)

### Phase 4 (Цель)
- [ ] Достичь 90%+ покрытия
- [ ] Автоматическая генерация тестов
- [ ] Mutation testing

---

📅 **Последнее обновление**: 17 августа 2025
🔖 **Версия**: 1.0.0
👤 **Автор**: BOT_AI_V3 Development Team