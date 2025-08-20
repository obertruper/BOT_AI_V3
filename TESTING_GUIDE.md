# 🎯 BOT_AI_V3 TESTING GUIDE

## 📖 Обзор

Полное руководство по тестированию системы BOT_AI_V3 с фокусом на Dynamic SL/TP компоненты и единую точку управления всеми тестами через оркестратор.

## 🚀 Быстрый старт

### Единая точка входа
```bash
# Интерактивный режим (рекомендуется)
python3 orchestrator_main.py

# Dynamic SL/TP тесты
python3 orchestrator_main.py --mode dynamic-sltp

# Быстрые тесты
python3 orchestrator_main.py --mode quick

# Полное тестирование
python3 orchestrator_main.py --mode full
```

### Интерактивное меню
После запуска `orchestrator_main.py` доступны опции:
- `[D]` - Dynamic SL/TP test suite 📊
- `[1]` - Run all enabled tests  
- `[4]` - Generate HTML report
- `[7]` - Full analysis (everything)

## 📊 Dynamic SL/TP Testing Suite

### Компоненты тестирования

#### 1. Unit Tests (`tests/unit/trading/orders/test_dynamic_sltp_calculator.py`)
Тестирует основную логику калькулятора:
- ATR расчеты и волатильность
- Различные режимы волатильности (low/medium/high)
- Адаптация SL/TP под confidence ML сигналов
- Валидация Risk/Reward соотношений

```bash
pytest tests/unit/trading/orders/test_dynamic_sltp_calculator.py -v -m "unit and sltp"
```

#### 2. Integration Tests (`tests/integration/test_dynamic_sltp_integration.py`)
Полная интеграция в торговую систему:
- ML сигнал → Dynamic SL/TP → Order creation
- Передача метаданных через всю цепочку
- Интеграция с PartialTPManager
- Тестирование различных рыночных режимов

```bash
pytest tests/integration/test_dynamic_sltp_integration.py -v -m "integration and sltp"
```

#### 3. E2E Tests (`tests/integration/test_dynamic_sltp_e2e.py`)  
End-to-end сценарии:
- WebSocket данные → ML обработка → Dynamic SL/TP → Order placement
- Адаптация к изменениям волатильности
- Обработка ошибок и восстановление
- Полные торговые сценарии

```bash  
pytest tests/integration/test_dynamic_sltp_e2e.py -v -m "e2e and sltp"
```

#### 4. Performance Tests (`tests/performance/test_dynamic_sltp_performance.py`)
Тесты производительности:
- Скорость одиночных расчетов (<100ms)
- Batch processing (50+ символов/сек)  
- Параллельная обработка (1.5x+ ускорение)
- Потребление памяти (<50MB для 100 расчетов)
- Stress тестирование (50+ calc/sec непрерывно)

```bash
pytest tests/performance/test_dynamic_sltp_performance.py -v -m "performance and sltp"
```

### Режимы запуска Dynamic SL/TP тестов

```bash
# Через оркестратор (интерактивно)
python3 orchestrator_main.py
# Выбрать [D] Dynamic SL/TP test suite

# Через CLI
python3 orchestrator_main.py --mode dynamic-sltp

# Через run_tests.py
python3 run_tests.py dynamic_sltp_quick    # Unit + Integration
python3 run_tests.py dynamic_sltp_complete # + E2E 
python3 run_tests.py dynamic_sltp_full     # + Performance
```

## 🗂️ Структура тестов

```
tests/
├── unit/
│   └── trading/orders/
│       └── test_dynamic_sltp_calculator.py    # Unit тесты
├── integration/  
│   ├── test_dynamic_sltp_integration.py       # Integration тесты
│   └── test_dynamic_sltp_e2e.py              # E2E тесты
├── performance/
│   └── test_dynamic_sltp_performance.py      # Performance тесты
└── fixtures/
    └── dynamic_sltp_fixtures.py              # Общие фикстуры
```

## 🎛️ Конфигурация pytest

### Маркеры (pytest.ini)
- `sltp` - Dynamic SL/TP тесты
- `unit` - Unit тесты
- `integration` - Integration тесты  
- `performance` - Performance тесты
- `e2e` - End-to-end тесты

### Примеры запуска с маркерами
```bash
# Все Dynamic SL/TP тесты
pytest -m sltp -v

# Unit тесты Dynamic SL/TP
pytest -m "unit and sltp" -v

# Все кроме performance
pytest -m "sltp and not performance" -v

# Integration и E2E  
pytest -m "(integration or e2e) and sltp" -v
```

## 📈 Ожидаемые результаты

### Unit Tests
- ✅ ATR расчеты корректны 
- ✅ Volatility режимы определяются правильно
- ✅ SL/TP адаптируются под confidence 
- ✅ Risk/Reward ratio >= 3.0
- ✅ Partial TP уровни логичны

### Integration Tests  
- ✅ Метаданные передаются через всю цепочку
- ✅ Orders создаются с правильными SL/TP
- ✅ Интеграция с ML сигналами работает
- ✅ PartialTPManager адаптируется к волатильности

### Performance Tests
- ✅ Один расчет < 100ms
- ✅ Batch processing > 50 символов/сек
- ✅ Параллельное ускорение > 1.5x  
- ✅ Memory usage < 50MB для 100 расчетов
- ✅ Stress test > 50 calc/sec

### E2E Tests
- ✅ Полный пайплайн работает
- ✅ Адаптация к волатильности  
- ✅ Error handling и recovery
- ✅ WebSocket → Order placement

## 🔧 Вспомогательные инструменты

### Unified Test Orchestrator
Главная точка управления:
```bash
# Интерактивный режим
python3 scripts/unified_test_orchestrator.py

# CLI режимы  
python3 scripts/unified_test_orchestrator.py --mode quick
python3 scripts/unified_test_orchestrator.py --mode full
```

### TestRunner (run_tests.py)
Централизованный запуск:
```bash
# Предопределенные цепочки
python3 run_tests.py quick            # Smoke + Unit
python3 run_tests.py standard         # Unit + ML + DB  
python3 run_tests.py full             # Все компоненты
python3 run_tests.py dynamic_sltp_quick # Dynamic SL/TP quick
```

### Фикстуры (tests/fixtures/dynamic_sltp_fixtures.py)
Общие компоненты для тестов:
- `dynamic_sltp_calculator` - Базовый калькулятор
- `sample_candles_*_volatility` - Данные с разной волатильностью
- `calculation_params` - Параметрические тесты
- `expected_results_validator` - Валидатор результатов
- `stress_test_scenarios` - Сценарии стресс-тестирования

## 📊 Отчетность

### HTML Dashboard
После запуска тестов генерируется `test_results/dashboard.html`:
- Общая статистика прохождения 
- Детализация по компонентам
- Performance метрики
- Coverage информация
- Timeline выполнения

### Доступ к отчетам
```bash
# Генерация после тестов
python3 orchestrator_main.py --mode quick --generate-report

# Только генерация отчета
python3 orchestrator_main.py --mode visual

# Открыть dashboard
open test_results/dashboard.html
```

## 🚨 Troubleshooting

### Частые проблемы

#### Import errors
```bash
# Убедитесь что venv активен
source venv/bin/activate
pip install -r requirements.txt
```

#### Тесты не находятся
```bash
# Проверьте PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH

# Запускайте из root директории
cd /mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3
python3 orchestrator_main.py
```

#### Performance тесты медленные  
Performance тесты по умолчанию отключены в оркестраторе.
Включите их вручную или используйте:
```bash
python3 orchestrator_main.py --mode performance
```

#### Database connection errors
```bash
# Проверьте порт PostgreSQL (должен быть 5555)
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT version();"

# Проверьте переменные окружения  
echo $PGPORT  # Должен быть 5555
```

### Логи и отладка

#### Verbose режим
```bash
# Подробный вывод
python3 orchestrator_main.py --mode dynamic-sltp --verbose

# Pytest с детальным выводом
pytest tests/unit/trading/orders/test_dynamic_sltp_calculator.py -v -s --tb=long
```

#### Фильтрация тестов
```bash
# Конкретный тест
pytest tests/unit/trading/orders/test_dynamic_sltp_calculator.py::TestDynamicSLTPCalculator::test_calculate_atr -v

# По имени функции
pytest -k "test_volatility" -v -m sltp
```

## ⚡ Best Practices

### 1. Порядок запуска тестов
1. `Unit tests` - быстрая проверка логики
2. `Integration tests` - проверка взаимодействий  
3. `E2E tests` - полные сценарии
4. `Performance tests` - только при необходимости

### 2. Использование маркеров
```bash
# Разработка - быстрые тесты
pytest -m "unit and sltp" -v

# Pre-commit - основные тесты
pytest -m "sltp and not performance" -v  

# Release - все тесты
pytest -m sltp -v
```

### 3. Параллельное выполнение
```bash  
# Для ускорения (если установлен pytest-xdist)
pytest -m sltp -n auto -v

# Через оркестратор  
python3 orchestrator_main.py --mode dynamic-sltp --parallel
```

### 4. Coverage анализ
```bash
# С coverage
pytest -m sltp --cov=trading.orders.dynamic_sltp_calculator --cov-report=html -v

# Через оркестратор
python3 orchestrator_main.py --mode coverage
```

## 🔗 Интеграция с CI/CD

### GitHub Actions пример
```yaml
name: Dynamic SL/TP Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run Dynamic SL/TP Tests  
      run: |
        python3 orchestrator_main.py --mode ci --quiet
        
    - name: Upload test results
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: test_results/
```

### Pre-commit hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
python3 orchestrator_main.py --mode quick --quiet
if [ $? -ne 0 ]; then
  echo "❌ Tests failed. Commit aborted."  
  exit 1
fi
```

## 📚 Дополнительные ресурсы

- [CLAUDE.md](CLAUDE.md) - Общее руководство по проекту
- [pytest documentation](https://docs.pytest.org/) - Документация pytest
- [scripts/unified_test_orchestrator.py](scripts/unified_test_orchestrator.py) - Исходный код оркестратора
- [tests/fixtures/dynamic_sltp_fixtures.py](tests/fixtures/dynamic_sltp_fixtures.py) - Тестовые фикстуры

## 🎯 Заключение

Dynamic SL/TP testing suite предоставляет комплексное тестирование всех аспектов динамических Stop Loss/Take Profit уровней:

- ✅ **Единая точка входа** через `orchestrator_main.py`
- ✅ **4 уровня тестирования** (Unit → Integration → E2E → Performance) 
- ✅ **Полная интеграция** в существующую тестовую систему
- ✅ **Визуальные отчеты** и детальная статистика
- ✅ **Гибкая конфигурация** через маркеры и режимы
- ✅ **CI/CD готовность** для автоматизации

Используйте интерактивный режим для разработки и CLI режимы для автоматизации.