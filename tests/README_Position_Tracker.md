# 🎯 Enhanced Position Tracker Test Suite

Комплексный набор тестов для системы отслеживания торговых позиций Enhanced Position Tracker.

## 🚀 Быстрый старт

### Запуск всех тестов

```bash
# Все тесты Position Tracker
python3 test_position_tracker.py

# С HTML отчетом
python3 test_position_tracker.py --html

# Через orchestrator
python3 orchestrator_main.py --mode position-tracker
```

### Выборочные тесты

```bash
# Только unit тесты (быстро)
python3 test_position_tracker.py --unit

# Только integration тесты
python3 test_position_tracker.py --integration

# Только performance тесты
python3 test_position_tracker.py --performance

# Быстрые тесты для CI
python3 test_position_tracker.py --quick
```

### С помощью pytest напрямую

```bash
# Все Position Tracker тесты
pytest -m position_tracker

# Только unit тесты
pytest -m "position_tracker and unit"

# Только performance тесты
pytest -m "position_tracker and performance"

# С подробным выводом
pytest -m position_tracker -v -s
```

## 📊 Структура тестов

### Unit Tests (`tests/unit/test_position_tracker.py`)

- ✅ Инициализация трекера
- ✅ Добавление/удаление позиций
- ✅ Расчет нереализованного PnL
- ✅ Проверка здоровья позиций
- ✅ Получение активных позиций
- ✅ Расчет метрик позиций
- ✅ Фабричная функция трекера

**Время выполнения:** ~2-5 секунд
**Зависимости:** Нет (все замокано)

### Integration Tests (`tests/integration/test_position_tracker_integration.py`)

- ✅ Интеграция с базой данных PostgreSQL
- ✅ Интеграция с ExchangeManager
- ✅ API интеграция (FastAPI endpoints)
- ✅ Синхронизация с биржами
- ✅ Жизненный цикл позиций
- ✅ Обработка ошибок

**Время выполнения:** ~10-20 секунд
**Зависимости:** PostgreSQL (мокнутый), Exchange API (мокнутый)

### Performance Tests (`tests/performance/test_position_tracker_performance.py`)

- ⚡ Скорость отслеживания позиций
- ⚡ Множественные позиции (до 2000)
- ⚡ Высокочастотные обновления
- ⚡ Использование памяти
- ⚡ Цикл мониторинга
- ⚡ Stress тесты

**Время выполнения:** ~30-60 секунд
**Зависимости:** psutil для мониторинга памяти

## 🎨 Отчеты и результаты

### HTML Dashboard

```bash
python3 test_position_tracker.py --html
```

Создает: `test_results/position_tracker_report.html`

### JSON отчеты

- `test_results/position_tracker_unit_report.json`
- `test_results/position_tracker_integration_report.json`
- `test_results/position_tracker_performance_report.json`

### Консольный отчет

```
================================================================================
🎯 ENHANCED POSITION TRACKER TEST RESULTS
================================================================================
📊 Общее время выполнения: 45.23s
🏆 Общий результат: ✅ УСПЕХ
📈 Процент успешности: 98.5%

📋 Статистика по типам тестов:
  ✅ Unit: 25/25 (3.45s)
  ✅ Integration: 15/15 (12.78s)
  ✅ Performance: 12/12 (28.99s)

🔢 Общая статистика:
  📝 Всего тестов: 52
  ✅ Пройдено: 51
  ❌ Провалено: 1
  ⏭️ Пропущено: 0
  💥 Ошибок: 0
```

## 🔧 Настройка и конфигурация

### Переменные окружения

```bash
# База данных (обязательно)
export PGPORT=5555
export PGUSER=obertruper
export PGDATABASE=bot_trading_v3

# API ключи бирж (для integration тестов)
export BYBIT_API_KEY=your_key
export BYBIT_API_SECRET=your_secret
export BYBIT_TESTNET=true
```

### Pytest конфигурация

Файл `pytest.ini` уже настроен с маркерами:

```ini
markers =
    position_tracker: Enhanced Position Tracker tests
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
```

## 🐛 Решение проблем

### Ошибки импорта

```bash
# Убедитесь что venv активирован
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### Ошибки базы данных

```bash
# Проверьте PostgreSQL на порту 5555
lsof -i :5555

# Запустите миграции
alembic upgrade head
```

### Таймауты тестов

```bash
# Увеличьте таймаут для медленных систем
pytest -m position_tracker --timeout=300
```

## 📈 Метрики производительности

### Ожидаемые показатели

- **Создание позиции:** < 100ms
- **Обновление метрик:** < 50ms
- **1000 позиций:** < 2s создание
- **Высокочастотные обновления:** > 100 ops/sec
- **Память на позицию:** < 0.1MB

### Benchmark тесты

```bash
# Запустить только performance тесты
python3 test_position_tracker.py --performance -v

# С профилированием
pytest -m "position_tracker and performance" --profile
```

## 🚀 Интеграция в CI/CD

### GitHub Actions

```yaml
- name: Run Position Tracker Tests
  run: |
    source venv/bin/activate
    python3 test_position_tracker.py --quick

- name: Generate Test Report
  run: |
    python3 test_position_tracker.py --html

- name: Upload Test Results
  uses: actions/upload-artifact@v3
  with:
    name: position-tracker-test-results
    path: test_results/
```

### Docker

```dockerfile
# Запуск тестов в контейнере
RUN python3 test_position_tracker.py --quick --html
```

## 📚 API Reference

### PositionTrackerTestSuite

```python
from tests.position_tracker_test_suite import PositionTrackerTestSuite

suite = PositionTrackerTestSuite()

# Запуск всех тестов
await suite.run_all_tests(verbose=True)

# Выборочные тесты
await suite.run_unit_tests()
await suite.run_integration_tests()
await suite.run_performance_tests()

# Отчеты
suite.print_summary()
await suite.generate_html_report()
```

## 🤝 Вклад в разработку

1. Добавляйте новые тесты в соответствующие файлы
2. Используйте pytest маркеры: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
3. Мокайте внешние зависимости в unit тестах
4. Добавляйте docstrings ко всем тестовым методам
5. Обновляйте этот README при добавлении новых тестов

## 📝 Лицензия

Часть проекта BOT_AI_V3. Все права защищены.
