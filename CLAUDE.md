# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Описание проекта

BOT Trading v3 - мульти-трейдерная платформа для автоматической торговли криптовалютой с AI-интеграцией. Миграция с BOT_Trading v2 в асинхронную архитектуру с поддержкой 7 бирж, множественных стратегий и Claude Code SDK автоматизацией.

**Масштаб**: ~673 Python файла, ~207,000 строк кода, 20+ основных модулей.

**Entry Points**:

- `python3 main.py` - основной торговый движок
- `python3 web/launcher.py` - веб-интерфейс
- `bot-trading` или `bot-trading-v3` - консольные команды из setup.py

## Ключевая архитектура

### Центральные компоненты (читать в первую очередь)

1. **TradingEngine** (`trading/engine.py`, 597 строк) - центральная координация всех торговых операций
2. **StrategyManager** (`strategies/manager.py`, 639 строк) - жизненный цикл стратегий с горячей заменой
3. **RiskManager** (`risk_management/manager.py`, 857 строк) - real-time мониторинг рисков с автоматическими действиями
4. **SystemOrchestrator** (`core/system/orchestrator.py`) - системная координация
5. **ExchangeRegistry** (`exchanges/registry.py`) - унифицированный доступ к 7 биржам

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
cd BOT_Trading_v3
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && npm install

# Настройка окружения
cp config/.env.example .env
# Отредактировать .env с API ключами

# Настройка базы данных
createdb bot_trading_v3
alembic upgrade head

# Запуск
python3 main.py                                    # Торговый движок
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

```bash
# Применение миграций
alembic upgrade head

# Создание новой миграции
alembic revision --autogenerate -m "Описание изменений"

# Откат миграции
alembic downgrade -1
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

### Ключевые конфигурации

- PostgreSQL 15+ подключение
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
- Создана БД: `createdb bot_trading_v3`
- Правильные credentials в `.env`

### WebSocket disconnects

- Проверьте стабильность интернет-соединения
- Увеличьте таймауты в `config/system.yaml`
- Проверьте лимиты API ключей бирж

**Версия**: 3.0.0-alpha
**Статус**: Active Development
**Последнее обновление**: 29 июля 2025
