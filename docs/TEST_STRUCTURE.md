# 🧪 Полная структура тестов и проверок BOT_AI_V3

## 📊 Обзор системы тестирования

При каждом `git push` автоматически запускается **289+ проверок** в 8 параллельных процессах.

## 🚀 1. PRE-COMMIT HOOKS (Перед коммитом)

Автоматически запускаются локально перед каждым коммитом:

### Базовые проверки

- ✅ **trailing-whitespace** - удаление пробелов в конце строк
- ✅ **end-of-file-fixer** - добавление новой строки в конец файла
- ✅ **check-yaml** - валидация YAML файлов
- ✅ **check-json** - валидация JSON файлов
- ✅ **check-toml** - валидация TOML файлов
- ✅ **check-added-large-files** - блокировка файлов >500KB
- ✅ **check-merge-conflict** - проверка маркеров конфликтов
- ✅ **check-case-conflict** - проверка конфликтов имён файлов
- ✅ **detect-private-key** - поиск приватных ключей
- ✅ **check-docstring-first** - docstring должен быть первым
- ✅ **debug-statements** - поиск забытых print/debugger
- ✅ **check-ast** - проверка синтаксиса Python

### Форматирование кода

- ✅ **Black** - автоформатирование Python (line-length=100)
- ✅ **Ruff** - быстрый линтер и форматтер
- ✅ **isort** - сортировка импортов

### Качество кода

- ✅ **MyPy** - статическая типизация
- ✅ **Bandit** - проверка безопасности
- ✅ **detect-secrets** - поиск секретов и паролей

### Другие языки

- ✅ **markdownlint** - проверка Markdown
- ✅ **yamllint** - линтинг YAML
- ✅ **eslint** - проверка JavaScript/TypeScript
- ✅ **commitizen** - проверка формата коммитов

## 🌐 2. CI/CD PIPELINE (GitHub Actions)

После push запускаются следующие workflow:

### 2.1 Pre-commit проверки

```yaml
Workflow: ci.yml -> pre-commit
```

- Запуск всех pre-commit хуков на всех файлах
- Время: ~2 минуты

### 2.2 Security Scan (Сканирование безопасности)

```yaml
Workflow: ci.yml -> security-scan
```

- **Bandit** - анализ уязвимостей Python кода
  - Проверяет: SQL инъекции, хардкод паролей, unsafe функции
  - Создаёт: bandit-report.json

- **Safety** - проверка известных уязвимостей в зависимостях
  - База данных CVE уязвимостей
  - Создаёт: safety-report.json

- **Semgrep** - статический анализ с правилами OWASP
  - Проверяет: OWASP Top 10, crypto ошибки
  - Создаёт: semgrep-report.json

### 2.3 Secrets Scan (Поиск секретов)

```yaml
Workflow: ci.yml -> secrets-scan
```

- **TruffleHog** - глубокое сканирование на утечки
  - Проверяет: API ключи, токены, пароли
  - Анализирует: всю историю git
  - Режим: only-verified (только подтверждённые)

### 2.4 Lint and Format (Проверка стиля)

```yaml
Workflow: ci.yml -> lint-and-format
```

- **Black** - проверка форматирования (не изменяет)
- **Ruff** - линтинг по 500+ правилам
- **Pylint** - глубокий анализ кода (минимум 8.0/10)
- **MyPy** - проверка типов для Python 3.12

### 2.5 Unit & Integration Tests (Тесты)

```yaml
Workflow: ci.yml -> test
```

Запускается в матрице для Python 3.10, 3.11, 3.12:

#### Окружение тестов

- PostgreSQL 15 на порту 5555
- Redis 7 на порту 6379
- Alembic миграции

#### Unit тесты (`tests/unit/`)

```bash
pytest tests/unit/ --cov=. --cov-report=xml -v
```

- **core/** - тесты orchestrator, system
- **database/** - тесты моделей и репозиториев
- **trading/** - тесты engine, orders, positions
- **exchanges/** - тесты API бирж
- **strategies/** - тесты стратегий
- **ml/** - тесты ML pipeline
- **utils/** - тесты утилит

#### Integration тесты (`tests/integration/`)

```bash
pytest tests/integration/ -v
```

- Тесты взаимодействия компонентов
- E2E сценарии торговли
- WebSocket тесты

#### Покрытие кода

- Минимум: 80% для новых файлов
- Отчёт: coverage.xml
- Загрузка в Codecov

### 2.6 Dependency Check (Проверка зависимостей)

```yaml
Workflow: ci.yml -> dependency-check
```

- **pip-audit** - аудит безопасности пакетов
- **pip-licenses** - проверка лицензий (создаёт licenses.md)

### 2.7 Code Quality (Метрики качества)

```yaml
Workflow: ci.yml -> code-quality
```

- **Radon CC** - цикломатическая сложность
  - A (1-5) простой код
  - B (6-10) слегка сложный
  - C (11-20) сложный
  - D (21-30) очень сложный

- **Radon MI** - индекс поддерживаемости
  - A (100-20) очень высокий
  - B (19-10) средний
  - C (9-0) низкий

- **Xenon** - контроль сложности
  - Максимум: B для модулей
  - Среднее: A для проекта

### 2.8 Docker Build (Сборка образа)

```yaml
Workflow: ci.yml -> docker-build
```

- Только для Pull Requests
- Тестовая сборка Docker образа
- Кэширование слоёв

## 🤖 3. CLAUDE CODE REVIEW (AI проверка)

### Автоматический review для PR

```yaml
Workflow: claude-code.yml
```

- Анализ изменений кода
- Поиск потенциальных проблем
- Предложения улучшений
- Ответы на @claude в комментариях

## 📁 4. СТРУКТУРА ТЕСТОВ

```
tests/
├── unit/                   # Модульные тесты
│   ├── core/              # Тесты ядра системы
│   │   ├── test_orchestrator_ml.py
│   │   └── test_system_components.py
│   ├── database/          # Тесты БД
│   │   ├── test_market_data_models.py
│   │   └── test_repositories.py
│   ├── trading/           # Тесты торговли
│   │   ├── orders/
│   │   │   ├── test_order_manager.py
│   │   │   └── test_sltp_integration.py
│   │   └── test_engine.py
│   ├── exchanges/         # Тесты бирж
│   │   ├── test_bybit.py
│   │   └── test_binance.py
│   ├── strategies/        # Тесты стратегий
│   │   └── test_patchtst_strategy.py
│   └── ml/               # Тесты ML
│       ├── test_feature_engineering.py
│       └── test_predictions.py
│
├── integration/           # Интеграционные тесты
│   ├── test_full_flow.py
│   ├── test_websocket.py
│   └── test_ml_pipeline.py
│
├── performance/          # Тесты производительности
│   ├── test_latency.py
│   └── test_throughput.py
│
├── fixtures/            # Фикстуры pytest
│   ├── __init__.py
│   └── ml_fixtures.py
│
├── scripts/            # Тестовые скрипты
│   ├── generate_test_signal.py
│   └── demo_system_work.py
│
└── conftest.py        # Конфигурация pytest
```

## 📈 5. МЕТРИКИ И ОТЧЁТЫ

### Генерируемые отчёты

- **coverage.xml** - покрытие кода
- **bandit-report.json** - уязвимости
- **safety-report.json** - CVE в зависимостях
- **semgrep-report.json** - OWASP проблемы
- **licenses.md** - лицензии пакетов

### Пороговые значения

- Покрытие кода: минимум 80%
- Pylint оценка: минимум 8.0/10
- Цикломатическая сложность: максимум B
- Размер файлов: максимум 500KB

## 🔧 6. ЛОКАЛЬНЫЙ ЗАПУСК ТЕСТОВ

### Запуск всех pre-commit хуков

```bash
pre-commit run --all-files
```

### Запуск unit тестов

```bash
pytest tests/unit/ -v --cov=.
```

### Запуск конкретного теста

```bash
pytest tests/unit/trading/test_engine.py::test_signal_processing -v
```

### Проверка безопасности

```bash
bandit -r . --skip B101,B601
safety check
```

### Проверка типов

```bash
mypy . --ignore-missing-imports
```

### Форматирование

```bash
black .
ruff check --fix .
```

## 📊 7. СТАТИСТИКА

### Общее количество проверок при push

- **15** pre-commit хуков
- **3** инструмента безопасности
- **1** сканер секретов
- **4** линтера кода
- **3** версии Python для тестов
- **50+** unit тестов
- **10+** integration тестов
- **3** метрики качества кода
- **2** проверки зависимостей

### Время выполнения

- Pre-commit: ~30 сек локально
- CI Pipeline: ~3-5 минут
- Полный прогон: ~5-7 минут

## 🚨 8. ОБРАБОТКА ОШИБОК

### При провале тестов

1. GitHub Actions блокирует merge
2. Создаётся отчёт с деталями
3. Claude Code предлагает исправления
4. Разработчик получает уведомление

### Игнорирование проверок (не рекомендуется)

```bash
# Коммит без pre-commit
git commit --no-verify

# Пропуск конкретной проверки
# В коде: # noqa: E501
# Или: # type: ignore
# Или: # nosec B101
```

## 📝 9. ДОБАВЛЕНИЕ НОВЫХ ТЕСТОВ

### Создание unit теста

```python
# tests/unit/my_module/test_my_feature.py
import pytest
from my_module import my_function

def test_my_function():
    result = my_function(input_data)
    assert result == expected_output

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Добавление в CI

1. Тесты автоматически подхватываются pytest
2. Добавить в `tests/unit/` или `tests/integration/`
3. Следовать naming convention: `test_*.py`

## ✅ 10. BEST PRACTICES

1. **Пишите тесты ДО кода** (TDD)
2. **Один тест - одна проверка**
3. **Используйте фикстуры** для повторяющихся данных
4. **Мокайте внешние сервисы** (биржи, БД)
5. **Проверяйте edge cases** и ошибки
6. **Держите покрытие >80%**
7. **Запускайте тесты локально** перед push

---

**Последнее обновление:** Август 2025
**Версия:** 3.0.0
