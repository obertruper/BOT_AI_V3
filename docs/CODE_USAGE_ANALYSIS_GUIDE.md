# 🔍 Code Usage Analysis System - Complete Guide

## Overview

Комплексная система анализа использования кода для BOT_AI_V3, которая помогает:

- 🚫 **Найти неиспользуемые файлы** - файлы которые не импортируются другими модулями
- 📅 **Найти устаревшие файлы** - файлы не изменявшиеся более N дней
- 🧹 **Безопасно очистить код** - с созданием резервных копий
- 📊 **Анализировать зависимости** - граф импортов между модулями

## 🚀 Quick Start

### 1. Запуск полного анализа

```bash
# Анализ с HTML и JSON отчетами
python3 scripts/run_code_usage_analysis.py --format both --verbose

# С генерацией скрипта очистки
python3 scripts/run_code_usage_analysis.py --format both --cleanup-script
```

### 2. Интерактивная очистка

```bash
# Безопасная интерактивная очистка
python3 scripts/interactive_code_cleanup.py
```

### 3. Просмотр результатов

- **JSON отчет**: `analysis_results/code_usage_analysis_YYYYMMDD_HHMMSS.json`
- **HTML отчет**: `analysis_results/code_usage_report_YYYYMMDD_HHMMSS.html`
- **Скрипт очистки**: `analysis_results/cleanup_script_YYYYMMDD_HHMMSS.sh`

## 📊 Analysis Results (Последний запуск)

### Статистика проекта

- **Всего Python файлов**: 521
- **Неиспользуемых файлов**: 117 (после фильтрации)
- **Файлов старше 1 дня**: 434
- **Файлов старше 1 недели**: 21
- **Файлов старше 1 месяца**: 0

### Время выполнения

- **Анализ проекта**: ~0.76 секунды
- **Производительность**: обрабатывает ~685 файлов/сек

## 🔧 Available Tools

### 1. Main Analyzer (`scripts/run_code_usage_analysis.py`)

**Возможности:**

- Сканирование всех Python файлов проекта
- AST-анализ импортов
- Построение графа зависимостей
- Детекция неиспользуемых файлов
- Анализ устаревших файлов по времени модификации

**Параметры:**

```bash
--format {json,html,both}  # Формат отчета (по умолчанию: both)
--verbose                  # Подробный вывод
--cleanup-script          # Генерация bash скрипта очистки
```

**Пример использования:**

```bash
# Полный анализ с подробным выводом
python3 scripts/run_code_usage_analysis.py --format both --verbose

# Только JSON отчет
python3 scripts/run_code_usage_analysis.py --format json

# С генерацией скрипта очистки
python3 scripts/run_code_usage_analysis.py --cleanup-script
```

### 2. Interactive Cleanup (`scripts/interactive_code_cleanup.py`)

**Возможности:**

- Интерактивный просмотр каждого файла
- Предварительный просмотр содержимого
- Группировка по категориям
- Автоматическое создание бэкапов
- Безопасное удаление с возможностью восстановления

**Режимы работы:**

1. **Interactive** - просмотр каждого файла отдельно
2. **By categories** - группировка похожих файлов
3. **Show list** - просто показать список и выйти

### 3. Test Validation (`tests/analysis/`)

**test_code_usage_analyzer.py** - Базовые тесты функциональности:

- Тест сканирования проекта
- Тест извлечения импортов
- Тест построения графа зависимостей
- Тест поиска неиспользуемых файлов

**test_code_analyzer_validation.py** - Валидация точности:

- Проверка точности на реальном проекте
- Тесты производительности
- Валидация результатов
- Проверка на ложные срабатывания

## 📂 File Categories & Filtering

### Автоматически исключаются

#### Entry Points

- `main.py`
- `unified_launcher.py`
- `app.py`, `wsgi.py`, `manage.py`

#### Test Files & Scripts

- Файлы с `test_` в названии
- Директории `tests/`, `testing/`
- Файлы в `scripts/`
- Файлы начинающиеся с `run_`
- `conftest.py`

#### System Files

- `__init__.py`
- Миграции (`migration`, `alembic`)
- Утилиты (`utils/`)
- AI агенты (`ai_agents/`)

#### Excluded Directories

- `__pycache__`, `.git`, `.venv`, `venv`
- `node_modules`, `.mypy_cache`, `.pytest_cache`
- `web/frontend`, `BOT_AI_V2`

## 🎯 Categories of Unused Files

### Debug Files

Файлы с `debug` в названии:

- `debug_ml_neutral_signals.py`
- `debug_real_sqrt_error.py`
- `debug_missing_features.py`

### Temporary Analysis

Временные файлы анализа:

- `analyze_*.py`
- `check_*.py`
- `final_*.py`
- Файлы с `temp` в названии

### Old Strategies

Неиспользуемые стратегии:

- `strategies/indicator_strategy/core/optimized_strategy.py`
- Другие файлы в `strategies/`

### ML Components

Неиспользуемые ML модули:

- `ml/signal_details_logger.py`
- `ml/logic/patchtst_usage_example.py`

### Configuration & Utilities

- `configure_metabase.py`
- Различные утилитарные скрипты

## 💾 Backup & Recovery

### Автоматические бэкапы

При использовании интерактивной очистки автоматически создается:

```
code_cleanup_backup_YYYYMMDD_HHMMSS/
├── [структура проекта с удаленными файлами]
└── restore.sh  # Скрипт восстановления
```

### Восстановление файлов

```bash
# Ручное восстановление
cp -r code_cleanup_backup_*/  ./

# Или через скрипт
bash code_cleanup_backup_*/restore.sh
```

## 📈 Performance Metrics

### Benchmark Results

- **Файлов обработано**: 521 Python файлов
- **Время сканирования**: ~0.3 секунды
- **Время анализа импортов**: ~0.45 секунды
- **Общее время**: ~0.76 секунды
- **Производительность**: ~685 файлов/сек

### Memory Usage

- **Пиковое использование памяти**: ~50MB
- **Граф зависимостей**: 956 связей между файлами
- **Изолированных файлов**: 169

## 🔒 Safety Features

### 1. Многоуровневая фильтрация

- Entry points никогда не удаляются
- Тестовые файлы исключаются
- Критические системные файлы защищены

### 2. Предварительный просмотр

- Просмотр содержимого файла перед удалением
- Информация о размере и дате изменения
- Интерактивный режим принятия решений

### 3. Backup System

- Автоматическое создание бэкапов
- Сохранение структуры директорий
- Скрипты восстановления

### 4. Validation Tests

- Автоматические тесты точности
- Проверка на ложные срабатывания
- Валидация производительности

## 🛠️ Advanced Usage

### Custom Import Analysis

```python
from scripts.run_code_usage_analysis import CodeUsageAnalyzer

analyzer = CodeUsageAnalyzer(project_root)
analyzer.scan_project()
analyzer.analyze_imports()

# Получить граф зависимостей
import_graph = analyzer.imports_graph
imported_by = analyzer.imported_by

# Найти неиспользуемые файлы
unused = analyzer.find_unused_files()

# Найти устаревшие файлы
stale_1w = analyzer.find_stale_files(7)
stale_1m = analyzer.find_stale_files(30)
```

### Custom Filtering

Для добавления собственных правил фильтрации:

```python
# В find_unused_files() добавить условия:
if 'custom_pattern' in file_key:
    continue  # Пропустить файл
```

### Integration with CI/CD

```yaml
# .github/workflows/code-analysis.yml
- name: Analyze code usage
  run: |
    python3 scripts/run_code_usage_analysis.py --format json
    # Проверить количество unused files
    unused_count=$(jq '.unused_files | length' analysis_results/code_usage_analysis_*.json | tail -1)
    if [ $unused_count -gt 200 ]; then
      echo "Too many unused files: $unused_count"
      exit 1
    fi
```

## 📋 Best Practices

### 1. Регулярный анализ

- Запускать анализ еженедельно
- Мониторить рост неиспользуемых файлов
- Интегрировать в CI/CD пайплайн

### 2. Безопасная очистка

- Всегда создавать бэкапы
- Тестировать после удаления файлов
- Начинать с очевидно неиспользуемых файлов

### 3. Категоризация

- Удалять debug файлы первыми
- Осторожно с ML компонентами
- Сохранять утилитарные скрипты

### 4. Validation

- Запускать тесты после очистки
- Проверять работоспособность системы
- Мониторить покрытие кода

## 🐛 Troubleshooting

### Проблема: Слишком много unused файлов

```bash
# Проверить фильтры
python3 -c "
from scripts.run_code_usage_analysis import CodeUsageAnalyzer
analyzer = CodeUsageAnalyzer('.')
print(f'Entry points: {analyzer.entry_points}')
print(f'Exclude dirs: {analyzer.exclude_dirs}')
"
```

### Проблема: Медленная работа

```bash
# Проверить количество файлов
find . -name "*.py" | wc -l

# Исключить большие директории
# Добавить в analyzer.exclude_dirs
```

### Проблема: Неточные результаты

```bash
# Запустить валидационные тесты
python3 -m pytest tests/analysis/test_code_analyzer_validation.py -v
```

## 🔄 Updates & Maintenance

### Version History

- **v1.0** - Базовый анализатор кода
- **v1.1** - Добавлена интерактивная очистка
- **v1.2** - Улучшена фильтрация, добавлены тесты валидации
- **v1.3** - Оптимизирована производительность

### Future Enhancements

- [ ] Анализ цикличных зависимостей
- [ ] Интеграция с Git для анализа истории изменений
- [ ] Web интерфейс для просмотра результатов
- [ ] Анализ размера и сложности файлов
- [ ] Автоматические рекомендации по рефакторингу

## 📞 Support

При возникновении проблем:

1. Проверить логи в `/data/logs/`
2. Запустить валидационные тесты
3. Проверить права доступа к файлам
4. Создать issue с подробным описанием

---

**Последнее обновление**: 2025-08-19
**Версия документации**: 1.3
**Совместимость**: Python 3.8+, BOT_AI_V3
