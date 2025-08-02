# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 КРИТИЧЕСКИ ВАЖНО

1. **PostgreSQL работает на порту 5555** (не стандартный 5432!)
2. **Всегда используй venv**: `source venv/bin/activate`
3. **НИКОГДА не коммить API ключи** - только через .env
4. **Весь код должен быть async/await** - синхронный код недопустим
5. **Используй TodoWrite для планирования** сложных задач

## Описание проекта

BOT Trading v3 - мульти-трейдерная платформа для автоматической торговли криптовалютой с AI-интеграцией. Миграция с BOT_Trading v2 в асинхронную архитектуру с поддержкой 7 бирж, множественных стратегий и Claude Code SDK автоматизацией.

**Масштаб**: ~673 Python файла, ~207,000 строк кода, 20+ основных модулей.

**Entry Points**:

- `python3 unified_launcher.py` - **единая система запуска всех компонентов**
- `python3 main.py` - основной торговый движок
- `python3 web/launcher.py` - веб-интерфейс
- `bot-trading` или `bot-trading-v3` - консольные команды из setup.py

## Ключевая архитектура

### Центральные компоненты (читать в первую очередь)

1. **UnifiedLauncher** (`unified_launcher.py:52`) - **главная точка входа для всей системы**
2. **ProcessManager** (`core/system/process_manager.py:42`) - управление дочерними процессами
3. **BotAIV3Application** (`main.py:32`) - основное торговое приложение
4. **SystemOrchestrator** (`core/system/orchestrator.py:44`) - системная координация всех компонентов
5. **TradingEngine** (`trading/engine.py:597`) - центральная координация всех торговых операций
6. **StrategyManager** (`strategies/manager.py:639`) - жизненный цикл стратегий с горячей заменой
7. **RiskManager** (`risk_management/manager.py:857`) - real-time мониторинг рисков с автоматическими действиями
8. **ExchangeRegistry** (`exchanges/registry.py`) - унифицированный доступ к 7 биржам
9. **Database connections** (`database/connections/postgres.py`) - синхронное и асинхронное подключение к БД

### Поток данных

```
Стратегии → SignalProcessor → TradingEngine → RiskManager → OrderManager → ExecutionEngine → Биржи
                ↓                   ↓              ↓
           Database ←          Monitoring ←    AI Agents
```

### Мульти-трейдерная архитектура

- Изолированные контексты для каждого трейдера через `TraderManager`
- Независимое управление стратегиями и рисками
- Централизованная координация через `SystemOrchestrator`

### AI-интеграция

- **Claude Code SDK** - полная интеграция для автоматизации
- **Cross-Verification System** - параллельная проверка через ChatGPT o3-pro, Grok v4, Claude Opus 4
- **4 специализированных агента**: CodeReviewer, TestGenerator, StrategyOptimizer, DocMaintainer
- **Автоактивация**: по слову "кросс" или для критических задач

## Команды разработки

### Быстрый старт

```bash
# Клонирование и установка
git clone <repository>
cd BOT_AI_V3
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && npm install

# Настройка окружения
cp .env.example .env
# Отредактировать .env с API ключами

# Настройка базы данных (PostgreSQL на порту 5555!)
# БД уже создана: bot_trading_v3, user: obertruper
# Если нужно создать заново:
# sudo -u postgres psql -p 5555 -c "CREATE DATABASE bot_trading_v3 OWNER obertruper;"
alembic upgrade head

# Запуск
python3 unified_launcher.py                       # 🚀 ЕДИНАЯ СИСТЕМА ЗАПУСКА
python3 unified_launcher.py --mode=core           # Только торговый движок
python3 unified_launcher.py --mode=api            # Только API + Frontend
python3 unified_launcher.py --mode=ml             # Core + ML без frontend
python3 unified_launcher.py --status              # Статус системы
python3 unified_launcher.py --logs                # Просмотр логов

# Альтернативные entry points
python3 main.py                                    # Основной торговый движок
python3 web/launcher.py --reload --debug          # Веб-интерфейс (dev)
bot-trading                                        # Entry point из setup.py

# Установка Node.js зависимостей для MCP серверов
npm install                                        # В корне проекта
```

### Тестирование

```bash
# Основные тесты
pytest tests/ --tb=short -v                       # Все тесты
pytest tests/unit/ --cov=src/ --cov-report=html   # Unit с покрытием
pytest tests/integration/ --slow                  # Интеграционные
pytest tests/performance/                         # Performance тесты
pytest tests/e2e/ --browser=chromium             # E2E с Playwright

# Единый тест
pytest tests/unit/test_specific.py::test_function -v

# Профилирование
python -m scripts.profile_trading_engine
python -m scripts.memory_analysis
python -m scripts.load_test --concurrent=100
```

### Production запуск

```bash
# Gunicorn (production)
gunicorn web.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Docker
docker build -t bot-trading-v3 .
docker-compose up -d

# Health check
curl http://localhost:8080/api/health
```

### Качество кода (обязательно перед коммитом)

```bash
# Автоформатирование
black .

# Проверка качества
ruff check .

# Автоисправление
ruff check --fix .

# Проверка типов
mypy src/

# Комплексная проверка
pre-commit run --all-files
```

### База данных

**ВАЖНО**: PostgreSQL работает на порту 5555 (не стандартный 5432!)

```bash
# Проверка подключения к БД
python3 -c "from database.connections import test_connection; test_connection()"

# Применение миграций
alembic upgrade head

# Создание новой миграции
alembic revision --autogenerate -m "Описание изменений"

# Откат миграции
alembic downgrade -1

# Визуализация структуры БД
python3 scripts/visualize_db.py

# Тест локального подключения
python3 scripts/test_local_db.py

# Прямой тест подключения
python3 database/connections/postgres.py
```

### AI агенты

```bash
# Автогенерация тестов
python3 -m ai_agents.test_generator --class=TradingEngine

# Ревью кода
python3 -m ai_agents.code_reviewer --file=trading/engine.py

# Кросс-верификация (3 минуты, параллельная обработка)
python3 -m ai_agents.cross_verification --task="Оптимальная стратегия скальпинга"

# Автоактивация по ключевому слову
python3 -m ai_agents.cross_verification --task="кросс: проверь архитектуру HFT"
```

### Отладка и мониторинг

```bash
# Логи (структурированные через structlog)
tail -f data/logs/trading.log
tail -f data/logs/error.log

# Метрики и мониторинг
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
# API docs: http://localhost:8080/api/docs

# Ротация API ключей
python -m scripts.rotate_api_keys --exchange=bybit

# Диагностика производительности
python -m scripts.benchmark_latency
python -m scripts.analyze_memory_usage
```

### Дополнительные возможности

```bash
# Установка дополнительных компонентов
pip install -e ".[monitoring]"    # Prometheus, Grafana, Sentry
pip install -e ".[telegram]"      # Telegram бот
pip install -e ".[docs]"          # Sphinx документация
pip install -e ".[dev]"           # Инструменты разработки

# Telegram бот (если установлен)
python -m monitoring.telegram_bot

# Генерация документации
sphinx-build -b html docs/ docs/_build/html/

# Синхронизация с сервером
bash scripts/sync_to_linux_server.sh  # Через SSH
bash scripts/sync_via_tailscale.sh    # Через Tailscale

# Frontend разработка
cd web/frontend
npm install                            # Установка зависимостей
npm run dev                            # Dev сервер (порт 5173)
npm run build                          # Production сборка
```

## 🚀 Unified Launcher - Единая система запуска

### Обзор

`unified_launcher.py` - центральная точка входа для управления всеми компонентами BOT_AI_V3:
- **Core System** (торговый движок + ML)
- **Web API** (FastAPI сервер)
- **Frontend** (React/Vite интерфейс)
- **Process Management** (автоматический перезапуск)
- **Health Monitoring** (проверка состояния компонентов)

### Режимы запуска

```bash
# Полная система (все компоненты)
python3 unified_launcher.py --mode=full

# Только торговля (Core + ML)
python3 unified_launcher.py --mode=core

# Только API и интерфейс
python3 unified_launcher.py --mode=api

# Торговля + ML без интерфейса
python3 unified_launcher.py --mode=ml

# Режим разработки (без автоперезапуска)
python3 unified_launcher.py --mode=dev
```

### Мониторинг и управление

```bash
# Статус всех компонентов
python3 unified_launcher.py --status

# Просмотр логов в реальном времени
python3 unified_launcher.py --logs

# Также доступны URL:
# Dashboard: http://localhost:5173
# API: http://localhost:8080
# API Docs: http://localhost:8080/api/docs
```

### Ключевые особенности

- **Автоматический перезапуск** процессов при сбоях (до 5 попыток)
- **Health checks** с проверкой готовности компонентов
- **Process isolation** - каждый компонент в отдельном процессе
- **Smart startup** - правильный порядок запуска с задержками
- **Resource monitoring** - отслеживание CPU, памяти, диска
- **PID management** - сохранение и отслеживание процессов

### Компоненты и конфигурация

Система автоматически настраивает:
- **Python пути** - правильное использование venv интерпретатора
- **Переменные окружения** - PYTHONPATH, UNIFIED_MODE
- **Порты** - API (8080), Frontend (5173)
- **Зависимости** - проверка PostgreSQL, Node.js, ML модели

### Исправленные проблемы

✅ **Критические ошибки исправлены**:
- ModuleNotFoundError: No module named 'passlib'
- AttributeError: 'ConfigManager' object has no attribute 'get_exchange_config'
- NameError: name 'os' is not defined
- Неправильный подсчет перезапусков процессов
- Использование системного Python вместо venv

### Архитектура процессов

```
UnifiedLauncher
├── ProcessManager (управление дочерними процессами)
├── HealthMonitor (проверка состояния)
├── Core Process (main.py)
├── API Process (web/launcher.py)
└── Frontend Process (npm run dev)
```

## MCP серверы (.mcp.json)

Проект настроен для работы с следующими MCP серверами:

- **filesystem** - доступ к файловой системе проекта
- **postgres** - работа с базой данных (порт 5555)
- **puppeteer** - браузерная автоматизация
- **sequential-thinking** - последовательное мышление для сложных задач
- **memory** - сохранение контекста между сессиями
- **github** - интеграция с GitHub API

## Claude Code Hooks (.claude/hooks.json)

Проект использует продвинутую систему хуков для автоматизации:

### PreToolUse хуки

- **Защита чувствительных файлов** - предупреждение при изменении .env, secrets, production конфигов
- **Логирование Bash команд** - все команды сохраняются в .claude/bash_history.log
- **Валидация стратегий** - напоминание о бэктестах при изменении strategies/

### PostToolUse хуки

- **Автоформатирование Python** - black, isort, ruff автоматически после сохранения
- **Автоформатирование React/TS** - prettier, eslint для frontend кода
- **Напоминание о тестах** - при изменении core модулей
- **Type checking** - mypy проверка после изменений Python файлов

### Полезные команды для хуков

```bash
claude-code test-hooks    # Тест конфигурации хуков
claude-code show-logs     # Показать последние логи
claude-code clean-logs    # Очистить логи
```

## Архитектурные принципы

### Модульность и разделение ответственности

- Каждый модуль имеет четко определенную зону ответственности
- Асинхронная архитектура для высокой производительности
- Thread-safe операции для многопоточности
- Dependency injection для тестируемости

### Конфигурация и безопасность

- Все секреты через переменные окружения (`.env`)
- Hot reload конфигурации без перезапуска
- Валидация всех входящих данных
- Rate limiting для API запросов

### Обработка ошибок

- Graceful degradation при сбоях бирж
- Comprehensive logging через structlog
- Prometheus метрики для мониторинга
- Автоматические алерты через PagerDuty/Slack

## Технологический стек

### Python 3.8+ (согласно setup.py)

- **FastAPI** - веб-API фреймворк
- **asyncpg + SQLAlchemy 2.0** - асинхронная работа с PostgreSQL 15+
- **ccxt** - универсальные биржевые API (7 бирж)
- **aiohttp** - асинхронные HTTP клиенты
- **structlog** - структурированное логирование
- **Redis** - кеширование и очереди
- **Alembic** - миграции БД

### AI и автоматизация

- **anthropic** - Claude Code SDK
- **xgboost** - машинное обучение (~63% точность)
- **MCP протоколы** - Playwright, Memory, Sequential Thinking
- **Cross-verification** - ChatGPT o3-pro, Grok v4, Claude Opus 4

### Мониторинг и производительность

- **Prometheus** - метрики (порт 9090)
- **Grafana** - дашборды (порт 3000)
- **Sentry** - error tracking
- **Performance**: 1000+ сигналов/сек, <50ms API латентность

### Node.js (MCP серверы)

- **@instantlyeasy/claude-code-sdk-ts** - TypeScript SDK
- **puppeteer** - браузерная автоматизация

### Frontend (web/)

- **React 18** с TypeScript
- **Vite** для сборки
- **Tailwind CSS** для стилей
- **Zustand** для state management

## Миграция с v2

Эта кодовая база представляет собой миграцию с BOT_Trading v2:

- Сохранена преемственность основной торговой логики
- Добавлена мульти-трейдерная поддержка
- Интегрирован Claude Code SDK
- Улучшена производительность и масштабируемость
- Расширена система рисков и мониторинга

## Правила разработки

### Обязательные требования

- Все новые функции должны иметь unit тесты
- Использовать type hints во всем Python коде
- Документировать все публичные функции и классы
- Проверять код линтерами перед коммитом (`black`, `ruff`, `mypy`)
- Никогда не коммитить секреты или API ключи

### AI-ассистированная разработка

- Использовать AI агентов для ревью кода и генерации тестов
- Активировать кросс-верификацию для критических изменений
- Поддерживать документацию через DocMaintainerAgent
- Оптимизировать стратегии через StrategyOptimizerAgent

### Отладка и мониторинг

- Структурированное логирование через structlog в `data/logs/`
- Prometheus метрики для ключевых показателей производительности
- Health checks для всех внешних зависимостей
- Comprehensive error handling с контекстной информацией

## Структура файлов данных

### Важные директории

- `data/logs/` - структурированные логи (trading.log, error.log)
- `data/cache/` - кэширование данных
- `data/temp/` - временные файлы
- `data/historical/` - исторические данные для бэктестинга
- `config/.env.example` - пример переменных окружения
- `tests/fixtures/` - тестовые фикстуры
- `docs/AI_VERIFICATION_REPORTS/` - отчеты кросс-верификации
- `.claude/` - логи и конфигурации Claude Code

### Ключевые конфигурации

- PostgreSQL 16 на порту 5555 (локальное подключение через Unix socket)
- База данных: `bot_trading_v3`, пользователь: `obertruper`
- Подключение БД: `postgresql://obertruper@:5555/bot_trading_v3` (без хоста для Unix socket)
- Redis для кеширования
- API ключи бирж (Bybit, Binance, OKX, Bitget, Gate.io, KuCoin, Huobi)
- Claude Code API ключ

## Языковые настройки

- Все комментарии в коде должны быть на русском языке
- Документация и объяснения - на русском языке
- Ответы и рекомендации давать на русском языке
- Названия переменных, функций и классов - на английском (стандарт)

---

## Частые проблемы и решения

### Import errors

- Убедитесь, что запускаете из корня проекта
- Активирована виртуальная среда: `source venv/bin/activate`
- Установлены все зависимости: `pip install -r requirements.txt`

### Database connection failed

- Проверьте PostgreSQL запущен: `systemctl status postgresql`
- PostgreSQL работает на порту 5555: `psql -p 5555 -U obertruper -d bot_trading_v3`
- Создана БД: `sudo -u postgres createdb bot_trading_v3`
- Правильные credentials в `.env` (user: obertruper, port: 5555)
- НЕ указывайте PGHOST для локального подключения через Unix socket

### WebSocket disconnects

- Проверьте стабильность интернет-соединения
- Увеличьте таймауты в `config/system.yaml`
- Проверьте лимиты API ключей бирж

## База данных - модели и структура

### Основные модели (`database/models/base_models.py`)

- **Order** - ордера с статусами (pending, open, filled, cancelled)
- **Trade** - исполненные сделки с PnL
- **Signal** - торговые сигналы от стратегий
- **Balance** - балансы по активам и биржам
- **Performance** - метрики производительности трейдеров

### Работа с БД

```python
# Синхронное подключение
from database.connections import get_db
with get_db() as db:
    orders = db.query(Order).all()

# Асинхронное подключение
from database.connections import get_async_db
async with get_async_db() as db:
    result = await db.execute(select(Order))

# Прямое подключение через asyncpg
from database.connections.postgres import AsyncPGPool
result = await AsyncPGPool.fetch("SELECT * FROM orders")
```

## Переменные окружения (.env)

Основные переменные окружения из `.env.example`:

```bash
# PostgreSQL (порт 5555!)
PGPORT=5555
PGUSER=obertruper
PGPASSWORD=your_password_here
PGDATABASE=bot_trading_v3

# Биржи
BYBIT_API_KEY, BYBIT_API_SECRET
BINANCE_API_KEY, BINANCE_API_SECRET
OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE
# ... и другие биржи

# AI сервисы
CLAUDE_API_KEY=your_claude_api_key
OPENAI_API_KEY=your_openai_api_key

# GitHub для MCP
GITHUB_TOKEN=your_github_token

# Системные настройки
LOG_LEVEL=INFO
ENVIRONMENT=development
DEFAULT_LEVERAGE=1
MAX_POSITION_SIZE=1000
RISK_LIMIT_PERCENTAGE=2
```

## ML компоненты (UnifiedPatchTST)

### Интегрированная ML модель

- **Модель**: UnifiedPatchTST из LLM TRANSFORM проекта
- **Параметры**: 240 входов → 20 выходов, контекст 96 (24 часа)
- **Производительность**: F1=0.414, Win Rate=46.6%
- **Файлы модели**: `models/saved/best_model_*.pth` (45MB)

### ML структура

```
ml/
├── logic/
│   ├── patchtst_model.py      # Архитектура модели
│   ├── feature_engineering.py # Генерация 240+ признаков
│   └── indicator_integration.py
├── strategies/ml_strategy/
│   ├── patchtst_strategy.py   # ML торговая стратегия
│   └── model_manager.py       # Управление моделями
└── config/ml/
    └── ml_config.yaml         # Конфигурация ML
```

### Использование ML стратегии

```bash
# Тестовый запуск
python scripts/run_ml_strategy.py --symbol BTCUSDT

# Боевой режим
python scripts/run_ml_strategy.py --symbol BTCUSDT --live

# Подготовка конфигурации модели
python scripts/prepare_model_config.py
```

Подробная документация: [docs/ML_INTEGRATION.md](docs/ML_INTEGRATION.md)

## 🤖 Специализированные агенты Claude Code

Проект настроен с продвинутой системой субагентов для различных задач:

### 🚨 ТЕКУЩАЯ ЗАДАЧА: Интеграция ML системы из LLM TRANSFORM

**Цель**: Создать систему генерации торговых сигналов каждую минуту с использованием UnifiedPatchTST модели
**Статус**: В процессе миграции компонентов из `/mnt/SSD/PYCHARMPRODJECT/LLM TRANSFORM/crypto_ai_trading`

### Доступные агенты

1. **trading-core-expert** - разработка торговой логики, стратегий, управление ордерами

   ```bash
   # Используй для: реализации новых стратегий, отладки торговой логики, оптимизации исполнения
   # ТЕКУЩЕЕ: Интеграция ML сигналов в торговую систему
   Task(description="Разработать grid trading стратегию", prompt="Создай новую grid trading стратегию для BTCUSDT", subagent_type="trading-core-expert")
   ```

2. **exchange-specialist** - интеграция с биржами, решение проблем с API

   ```bash
   # Используй для: добавления новых бирж, исправления проблем с подключением, оптимизации API вызовов
   # ТЕКУЩЕЕ: Загрузка OHLCV данных для ML модели
   Task(description="Исправить Bybit WebSocket", prompt="WebSocket отключается каждые 5 минут на Bybit", subagent_type="exchange-specialist")
   ```

3. **ml-optimizer** - работа с ML моделями, оптимизация PatchTST, feature engineering

   ```bash
   # Используй для: улучшения ML стратегий, добавления новых признаков, оптимизации гиперпараметров
   # ТЕКУЩЕЕ: Адаптация UnifiedPatchTST и feature_engineering.py для BOT_AI_V3
   Task(description="Оптимизировать ML модель", prompt="Улучшить точность PatchTST модели", subagent_type="ml-optimizer")
   ```

4. **security-guardian** - аудит безопасности, защита API ключей, валидация

   ```bash
   # Используй для: security аудита, проверки на уязвимости, настройки защиты
   Task(description="Security аудит", prompt="Проверить систему на уязвимости безопасности", subagent_type="security-guardian")
   ```

5. **performance-tuner** - оптимизация производительности, профилирование, кеширование

   ```bash
   # Используй для: устранения узких мест, оптимизации скорости, настройки кеширования
   # ТЕКУЩЕЕ: Оптимизация обработки 240+ признаков каждую минуту
   Task(description="Оптимизировать API", prompt="API endpoints работают медленно", subagent_type="performance-tuner")
   ```

6. **database-architect** - проектирование и оптимизация БД PostgreSQL

   ```bash
   # Используй для: создания миграций, оптимизации запросов, настройки индексов
   # ТЕКУЩЕЕ: Создание таблиц raw_market_data, processed_market_data
   Task(description="Оптимизировать БД", prompt="Создать эффективную структуру для хранения OHLCV данных", subagent_type="database-architect")
   ```

### Кастомные команды (slash commands)

- `/check-exchange-health` - проверка здоровья всех бирж
- `/analyze-trading-performance` - анализ производительности стратегий
- `/security-scan` - полный security аудит
- `/optimize-ml-model` - оптимизация ML модели

### Примеры использования цепочек агентов

```bash
# Добавление новой биржи
1. Task(..., subagent_type="exchange-specialist")  # Реализация адаптера
2. Task(..., subagent_type="security-guardian")    # Проверка безопасности
3. Task(..., subagent_type="performance-tuner")    # Оптимизация

# Разработка новой ML стратегии
1. Task(..., subagent_type="ml-optimizer")         # Создание модели
2. Task(..., subagent_type="trading-core-expert")  # Интеграция в систему
3. Task(..., subagent_type="performance-tuner")    # Оптимизация inference
```

**Версия**: 3.0.0-alpha
**Статус**: Active Development
**Последнее обновление**: 2 августа 2025

## 📋 Завершенные задачи (2 августа 2025)

### ✅ Unified Launcher System - ЗАВЕРШЕНО

**Результат**: Создана единая система запуска для всех компонентов BOT_AI_V3

**Реализованные компоненты**:
1. ✅ **UnifiedLauncher** (`unified_launcher.py`) - главная точка входа
2. ✅ **ProcessManager** (`core/system/process_manager.py`) - управление процессами  
3. ✅ **Исправления критических ошибок**:
   - ❌ → ✅ ModuleNotFoundError: No module named 'passlib'
   - ❌ → ✅ ConfigManager.get_exchange_config method missing
   - ❌ → ✅ NameError: name 'os' is not defined
   - ❌ → ✅ Неправильный подсчет перезапусков процессов
   - ❌ → ✅ Использование системного Python вместо venv

**Возможности**:
- 🚀 Единая команда запуска: `python3 unified_launcher.py`
- 🔄 Автоматический перезапуск при сбоях (до 5 попыток)
- 📊 Мониторинг состояния: `--status`, `--logs`
- 🎯 Режимы запуска: `--mode=full/core/api/ml/dev`
- 💻 Изоляция процессов с health checks
- 📈 Системные метрики (CPU, память, диск)

## 📋 Текущие задачи разработки

### Интеграция ML системы из LLM TRANSFORM

**Задача**: Перенести и адаптировать систему генерации торговых сигналов из проекта LLM TRANSFORM

**Компоненты для переноса**:

1. ✅ **Модель UnifiedPatchTST** - `ml/logic/patchtst_model.py`
2. ✅ **Feature Engineering** - `ml/logic/feature_engineering.py` (240+ признаков)
3. ✅ **Модели БД** - `database/models/market_data.py` (raw_market_data, processed_market_data)
4. ✅ **DataLoader** - `data/data_loader.py` (загрузка OHLCV с бирж)
5. ⏳ **DataProcessor** - обработка данных и расчет индикаторов
6. ⏳ **MLSignalGenerator** - генерация торговых сигналов
7. ⏳ **SignalScheduler** - запуск каждую минуту

**Особенности реализации**:

- Весь код должен быть **async/await**
- PostgreSQL на порту **5555**
- Использовать существующую инфраструктуру BOT_AI_V3
- Интеграция с SystemOrchestrator
- Поддержка множественных символов (50+ из ml_config.yaml)

**Рекомендуемые агенты для задач**:

- `ml-optimizer` - для работы с ML компонентами
- `database-architect` - для оптимизации БД
- `trading-core-expert` - для интеграции сигналов
- `performance-tuner` - для оптимизации производительности
