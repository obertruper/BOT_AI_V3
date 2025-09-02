# 🚀 Единая система тестирования BOT_AI_V3

## ✨ Одна точка входа для всех тестов

Все тесты BOT_AI_V3 теперь запускаются через единый оркестратор:

```bash
python3 scripts/unified_test_orchestrator.py
```

## 🎯 Доступные режимы

### 1. Интерактивный режим (по умолчанию)

```bash
python3 scripts/unified_test_orchestrator.py
# или
python3 scripts/unified_test_orchestrator.py --mode interactive
```

**Возможности:**

- Визуальное меню с выбором компонентов
- Включение/отключение отдельных тестов
- Генерация HTML отчетов
- Очистка результатов

### 2. Быстрое тестирование

```bash
python3 scripts/unified_test_orchestrator.py --mode quick
```

Запускает только базовые unit тесты.

### 3. Полный анализ

```bash
python3 scripts/unified_test_orchestrator.py --mode full-analysis
```

Запускает все доступные тесты и проверки.

### 4. ML тестирование

```bash
python3 scripts/unified_test_orchestrator.py --mode ml
```

Фокусируется на ML компонентах и связанных тестах.

### 5. Анализ кода (НОВОЕ!)

```bash
python3 scripts/unified_test_orchestrator.py --mode code-analysis
```

Запускает систему анализа использования кода:

- Тесты анализатора кода
- Валидационные тесты
- Полный отчет по неиспользуемым файлам

## 📊 Текущие результаты (последний запуск)

### Общая статистика

- **Всего тестов**: 357
- **Успешных**: 335 (93.8%)
- **Частично успешных**: 22 (6.2%)
- **Покрытие кода**: 9.0%
- **Время выполнения**: 57.5 секунд
- **Компонентов успешно**: 20/24 (83.3%)

### Компоненты тестирования

#### ✅ Полностью успешные (20 компонентов)

- 🧪 Unit Tests
- 🗄️ Database Tests
- 📈 Trading Tests
- 🧠 ML System Tests
- 🔗 Integration Tests
- ⚡ Performance Tests
- ✨ Code Quality Check
- 🔍 Type Checking
- 📊 Coverage Report
- 🔐 Security Check
- ⚙️ Feature Engineering Tests
- 🔄 Exchanges System Tests
- 🌐 Web API Tests
- 🎯 Core Orchestrator Tests
- ⚡ Trading Engine Tests
- 🎯 Main Application Tests
- 🚀 Unified Launcher Tests
- **🔍 Code Usage Analyzer Tests (НОВОЕ!)**
- **✅ Code Analyzer Validation Tests (НОВОЕ!)**
- **📊 Code Usage Analysis Report (НОВОЕ!)**

#### ⚠️ Частично успешные (4 компонента)

- 🧠 ML Manager Tests
- ⚙️ Core System Tests
- 📊 ML Prediction Logger Tests
- 🧠 ML Manager Enhanced Tests

## 🎛️ Интерактивное меню

При запуске без параметров открывается интерактивное меню:

```
📋 Test Components:
✅ 🧪 Unit Tests                    [unit_tests]
✅ 🗄️ Database Tests               [database_tests]
✅ 📈 Trading Tests                [trading_tests]
...
✅ 🔍 Code Usage Analyzer Tests    [code_usage_analyzer_tests]
✅ ✅ Code Analyzer Validation Tests [code_analyzer_validation_tests]
⭕ 📊 Code Usage Analysis Report   [code_analysis_report]

⚙️  Options:
  [1] Run all enabled tests
  [2] Toggle component on/off
  [3] Run specific component
  [4] Generate HTML report
  [5] Clean previous results
  [6] Quick test (unit only)
  [7] Full analysis (everything)
  [8] Visual dashboard
  [9] Code analysis suite ← НОВОЕ!
  [0] Exit
```

## 🔧 CLI параметры

```bash
# Основные режимы
python3 scripts/unified_test_orchestrator.py --mode {interactive|full|full-analysis|quick|visual|ml|code-analysis}

# Очистка результатов перед запуском
python3 scripts/unified_test_orchestrator.py --mode full --clean

# Примеры
python3 scripts/unified_test_orchestrator.py --mode quick --clean
python3 scripts/unified_test_orchestrator.py --mode code-analysis
python3 scripts/unified_test_orchestrator.py --mode full-analysis
```

## 📈 Анализ кода - Новые возможности

### Что включает режим `code-analysis`

1. **Code Usage Analyzer Tests** (12 тестов)
   - Тестирование сканирования проекта
   - Валидация извлечения импортов
   - Проверка построения графа зависимостей

2. **Code Analyzer Validation Tests** (11 тестов)
   - Проверка точности на реальном проекте
   - Валидация производительности
   - Тесты на ложные срабатывания

3. **Code Usage Analysis Report**
   - Полный анализ 521 Python файла
   - Выявление 117 неиспользуемых файлов
   - HTML и JSON отчеты
   - Анализ устаревших файлов

### Результаты анализа кода

- **Время анализа**: ~0.76 секунды
- **Найдено неиспользуемых файлов**: 117
- **Файлов старше недели**: 21
- **Производительность**: 685+ файлов/сек
- **Все тесты**: ✅ УСПЕШНО

## 📊 HTML Dashboard

После каждого запуска генерируется интерактивный HTML dashboard:

```
test_results/dashboard.html
```

**Содержит:**

- Визуальную статистику
- Статус всех компонентов
- График покрытия кода
- Временные метки

## 🚀 Быстрые команды

```bash
# Самый быстрый способ запустить все тесты
python3 scripts/unified_test_orchestrator.py --mode full

# Только анализ кода
python3 scripts/unified_test_orchestrator.py --mode code-analysis

# Интерактивный режим с меню
python3 scripts/unified_test_orchestrator.py

# Очистка + полный анализ
python3 scripts/unified_test_orchestrator.py --mode full-analysis --clean
```

## 📁 Структура результатов

```
test_results/
├── dashboard.html                    # Интерактивный dashboard
├── test_report_YYYYMMDD_HHMMSS.json # JSON отчет с деталями
└── coverage.json                    # Данные покрытия кода

analysis_results/
├── code_usage_analysis_*.json       # JSON анализ кода
├── code_usage_report_*.html         # HTML отчет анализа
└── cleanup_script_*.sh              # Скрипт очистки (если создан)
```

## 🎯 Следующие шаги

### Для улучшения покрытия (текущее: 9.0%)

1. Запустить автогенератор тестов:

   ```bash
   python3 scripts/mass_test_generator.py
   ```

2. Сфокусироваться на критических компонентах:
   - `trading/` - торговая логика
   - `ml/` - ML компоненты
   - `exchanges/` - интеграции бирж

### Для анализа кода

1. Запустить интерактивную очистку:

   ```bash
   python3 scripts/interactive_code_cleanup.py
   ```

2. Просмотреть HTML отчет анализа кода

## 🛠️ Troubleshooting

### Проблема: Тесты не запускаются

```bash
# Проверить виртуальное окружение
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### Проблема: Низкое покрытие кода

```bash
# Запустить генератор тестов
python3 scripts/mass_test_generator.py

# Или использовать интерактивный режим для выбора конкретных компонентов
python3 scripts/unified_test_orchestrator.py
```

### Проблема: Ошибки ML тестов

```bash
# Проверить ML зависимости
pip install torch numpy pandas scikit-learn

# Запустить только ML тесты
python3 scripts/unified_test_orchestrator.py --mode ml
```

## 📞 Support

При проблемах:

1. Проверить логи в `test_results/`
2. Запустить в интерактивном режиме для диагностики
3. Использовать `--clean` для сброса состояния

---

**Версия**: 1.4
**Последнее обновление**: 2025-08-19
**Всего компонентов**: 24
**Всего тестов**: 357
