# 🧪 Руководство по тестированию BOT_AI_V3

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Структура тестов](#структура-тестов)
3. [Запуск тестов](#запуск-тестов)
4. [Цепочки тестов](#цепочки-тестов)
5. [Маркеры тестов](#маркеры-тестов)
6. [Написание тестов](#написание-тестов)
7. [Покрытие кода](#покрытие-кода)
8. [CI/CD интеграция](#cicd-интеграция)
9. [Лучшие практики](#лучшие-практики)

## 🚀 Быстрый старт

### Установка зависимостей для тестирования

```bash
# Установить dev зависимости
pip install -e ".[dev]"

# Или через make
make dev-install
```

### Запуск всех тестов

```bash
# Через pytest
pytest

# Через make
make test-all

# Через test runner
python run_tests.py
```

### Запуск конкретных тестов

```bash
# Unit тесты
pytest tests/unit/
make test-unit

# ML тесты
pytest tests/unit/ml/
make test-ml

# Быстрые тесты
make test-quick
```

## 📁 Структура тестов

```
tests/
├── conftest.py          # Глобальные fixtures
├── fixtures/            # Тестовые данные и утилиты
│   └── ml_fixtures.py   # ML-специфичные fixtures
├── unit/               # Unit тесты
│   ├── core/           # Тесты core компонентов
│   ├── database/       # Тесты БД
│   ├── ml/             # Тесты ML компонентов
│   ├── exchanges/      # Тесты бирж
│   ├── strategies/     # Тесты стратегий
│   └── utils/          # Тесты утилит
├── integration/        # Интеграционные тесты
├── performance/        # Performance тесты
└── e2e/               # End-to-end тесты
```

## 🏃 Запуск тестов

### Использование pytest напрямую

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# Конкретный файл
pytest tests/unit/ml/test_ml_manager.py

# Конкретный тест
pytest tests/unit/ml/test_ml_manager.py::TestMLManager::test_initialization

# По маркеру
pytest -m ml
pytest -m "unit and not slow"

# С покрытием
pytest --cov=. --cov-report=html
```

### Использование Makefile

```bash
# Основные команды
make test          # Unit тесты
make test-all      # Все тесты
make test-ml       # ML тесты
make test-coverage # С покрытием
make test-chain    # Цепочка тестов

# Специальные команды
make test-quick    # Быстрые тесты
make test-watch    # Watch режим
make test-failed   # Перезапуск проваленных
make test-parallel # Параллельный запуск
```

### Использование test runner

```bash
# Запуск стандартной цепочки
python run_tests.py

# Конкретный набор
python run_tests.py --suite ml

# Предопределенная цепочка
python run_tests.py --chain quick
python run_tests.py --chain full

# Кастомная цепочка
python run_tests.py --chain unit,ml,database

# Списки
python run_tests.py --list-suites
python run_tests.py --list-chains

# С отчетом покрытия
python run_tests.py --coverage
```

## 🔗 Цепочки тестов

### Предопределенные цепочки

- **quick**: smoke → unit (быстрая проверка)
- **standard**: unit → ml → database (стандартная)
- **full**: unit → ml → database → integration → performance (полная)
- **ml-focus**: ml → database → integration (ML фокус)
- **ci**: smoke → unit → ml (для CI/CD)

### Создание кастомных цепочек

```bash
# Через запятую
python run_tests.py --chain unit,database,ml

# Без остановки при ошибке
python run_tests.py --chain full --no-stop
```

## 🏷️ Маркеры тестов

### Основные маркеры

```python
@pytest.mark.unit          # Unit тесты
@pytest.mark.integration   # Интеграционные тесты
@pytest.mark.performance   # Performance тесты
@pytest.mark.ml           # ML тесты
@pytest.mark.slow         # Медленные тесты (>5 сек)
@pytest.mark.smoke        # Smoke тесты
```

### Специальные маркеры

```python
@pytest.mark.requires_db       # Требует БД
@pytest.mark.requires_gpu      # Требует GPU
@pytest.mark.requires_exchange # Требует API биржи
```

### Использование маркеров

```python
# В тесте
@pytest.mark.ml
@pytest.mark.slow
class TestMLPipeline:
    def test_full_pipeline(self):
        pass

# Запуск
pytest -m ml                    # Только ML
pytest -m "ml and not slow"     # ML но не медленные
pytest -m "unit or smoke"       # Unit или smoke
```

## ✍️ Написание тестов

### Структура теста

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

class TestMLManager:
    """Тесты для MLManager"""

    @pytest.fixture
    def ml_manager(self):
        """Fixture для MLManager"""
        return MLManager()

    def test_initialization(self, ml_manager):
        """Тест инициализации"""
        assert ml_manager is not None

    @pytest.mark.asyncio
    async def test_async_method(self, ml_manager):
        """Тест асинхронного метода"""
        result = await ml_manager.async_method()
        assert result is True
```

### Использование fixtures

```python
# Глобальные fixtures из conftest.py
def test_with_ml_model(mock_ml_model, sample_ohlcv_data):
    """Тест с использованием глобальных fixtures"""
    predictions = mock_ml_model(sample_ohlcv_data)
    assert predictions.shape == (1, 20)

# Локальные fixtures
@pytest.fixture
def trading_signal():
    return Signal(symbol="BTCUSDT", confidence=0.8)
```

### Параметризованные тесты

```python
@pytest.mark.parametrize("input,expected", [
    (0, "LONG"),
    (1, "SHORT"),
    (2, "FLAT"),
])
def test_signal_types(input, expected):
    assert SignalType(input).name == expected
```

## 📊 Покрытие кода

### Генерация отчета

```bash
# HTML отчет
pytest --cov=. --cov-report=html
# Открыть: htmlcov/index.html

# Терминал отчет
pytest --cov=. --cov-report=term-missing

# XML для CI
pytest --cov=. --cov-report=xml
```

### Настройки покрытия

В `pytest.ini`:

```ini
[coverage:run]
source = .
omit =
    */tests/*
    */migrations/*
    setup.py
```

### Минимальное покрытие

```bash
# Требовать минимум 70% покрытия
pytest --cov=. --cov-fail-under=70
```

## 🔄 CI/CD интеграция

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    - name: Run tests
      run: |
        python run_tests.py --chain ci
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: tests
        entry: make test-quick
        language: system
        pass_filenames: false
        always_run: true
```

## 📚 Лучшие практики

### 1. Изоляция тестов

```python
# Плохо - тесты зависят друг от друга
def test_create_user():
    user = User.create("test")

def test_delete_user():
    user = User.get("test")  # Зависит от предыдущего
    user.delete()

# Хорошо - независимые тесты
def test_create_user(db_session):
    user = User.create("test")
    assert user.name == "test"

def test_delete_user(db_session):
    user = User.create("test")
    user.delete()
    assert User.get("test") is None
```

### 2. Использование моков

```python
# Mock внешних зависимостей
@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.json.return_value = {"price": 50000}
    result = get_btc_price()
    assert result == 50000
```

### 3. Асинхронные тесты

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

### 4. Группировка тестов

```python
class TestMLPipeline:
    """Группировка связанных тестов"""

    def test_data_loading(self):
        pass

    def test_feature_engineering(self):
        pass

    def test_model_prediction(self):
        pass
```

### 5. Именование тестов

```python
# Плохо
def test1():
    pass

# Хорошо
def test_ml_manager_initialization_with_default_config():
    pass
```

## 🛠️ Отладка тестов

### Запуск с отладкой

```bash
# Остановка на первой ошибке
pytest -x

# Показать print() выводы
pytest -s

# Подробный traceback
pytest --tb=long

# PDB отладчик при ошибке
pytest --pdb
```

### VS Code конфигурация

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

## 📈 Мониторинг качества

### Метрики

- **Покрытие кода**: минимум 80%
- **Время выполнения**: < 5 минут для unit тестов
- **Успешность**: 100% для main ветки

### Команды проверки

```bash
# Проверка покрытия
make test-coverage

# Анализ медленных тестов
pytest --durations=10

# Проверка маркеров
pytest --markers
```

## 🔧 Troubleshooting

### Частые проблемы

1. **Import errors**

   ```bash
   # Установить проект в dev режиме
   pip install -e .
   ```

2. **Database errors**

   ```bash
   # Проверить миграции
   alembic upgrade head
   ```

3. **Async warnings**

   ```python
   # Использовать правильный маркер
   @pytest.mark.asyncio
   ```

4. **Fixture not found**

   ```python
   # Проверить conftest.py
   # Проверить область видимости fixture
   ```

---

📝 **Примечание**: Регулярно обновляйте тесты при изменении кода и следите за покрытием!
