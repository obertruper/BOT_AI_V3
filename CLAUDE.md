# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 КРИТИЧЕСКИ ВАЖНО - ПРОВЕРЯЙ ПЕРЕД КАЖДЫМ ДЕЙСТВИЕМ

1. **PostgreSQL порт 5555** - НЕ 5432! Всегда: `PGPORT=5555`
2. **Активируй venv первым**: `source venv/bin/activate` перед ЛЮБОЙ командой
3. **API ключи ТОЛЬКО в .env** - проверяй перед коммитом: `git diff --staged | grep -i "api_key\|secret"`
4. **Только async/await код** - используй `async def`, `await`, `asyncio`
5. **TodoWrite обязателен** для задач с 3+ шагами

## О проекте

BOT Trading v3 - высокопроизводительная платформа алгоритмической торговли криптовалютами с ML-предсказаниями и мульти-биржевой поддержкой.

**Масштаб**: 673 файла, 207K+ строк, Python 3.8+, PostgreSQL 15+, 7 бирж, 50+ торговых пар

**🚀 Главная точка входа**: `python3 unified_launcher.py` (управляет всеми компонентами)

## 🏗️ Архитектура (КРИТИЧНО для понимания)

### Поток выполнения торговых операций

```
1. UnifiedLauncher запускает все процессы
2. SystemOrchestrator координирует компоненты
3. Стратегии генерируют сигналы → TradingEngine обрабатывает
4. RiskManager проверяет → OrderManager создает ордера
5. ExecutionEngine исполняет → Биржи получают команды
6. Результаты → База данных (PostgreSQL:5555)
```

### 5 ключевых файлов для начала работы

| Файл | Назначение | Строка входа |
|------|------------|--------------|
| `unified_launcher.py` | Запуск всей системы | :52 class UnifiedLauncher |
| `main.py` | Торговое ядро | :32 class BotAIV3Application |
| `core/system/orchestrator.py` | Координация | :44 class SystemOrchestrator |
| `trading/engine.py` | Торговая логика | :597 class TradingEngine |
| `database/connections/postgres.py` | БД подключение | Async/sync pools |

### Асинхронная архитектура

- **Все I/O операции async**: биржи, БД, файлы
- **Пулы подключений**: asyncpg для PostgreSQL, aiohttp для API
- **Graceful shutdown**: сохранение состояния при остановке

## 🛠️ Команды для работы

### Первый запуск (3 минуты)

```bash
# 1. Подготовка окружения
cd BOT_AI_V3
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Конфигурация
cp .env.example .env
# Редактируй .env - добавь хотя бы один API ключ биржи

# 3. БД уже настроена (PostgreSQL:5555, user: obertruper)
alembic upgrade head

# 4. Запуск системы
python3 unified_launcher.py  # Запустит все компоненты
```

### Режимы запуска unified_launcher.py

```bash
python3 unified_launcher.py              # Все компоненты (trading + API + frontend)
python3 unified_launcher.py --mode=core  # Только торговля
python3 unified_launcher.py --mode=api   # Только API/веб
python3 unified_launcher.py --mode=ml    # Торговля + ML
python3 unified_launcher.py --status     # Проверка статуса
python3 unified_launcher.py --logs       # Следить за логами
```

### Тестирование

```bash
# Быстрый тест конкретной функции
pytest tests/unit/test_trading_engine.py -k "test_signal_processing" -v

# Все unit тесты с покрытием
pytest tests/unit/ --cov=. --cov-report=term-missing

# Запуск конкретного теста
pytest path/to/test.py::TestClass::test_method
```

### Качество кода - ЗАПУСКАЙ ПЕРЕД КОММИТОМ

```bash
# 1. Форматирование (обязательно)
black . && ruff check --fix .

# 2. Проверка типов
mypy . --ignore-missing-imports

# 3. Поиск секретов
git diff --staged | grep -i "api_key\|secret\|password"
```

### База данных PostgreSQL:5555

```bash
# Быстрая проверка подключения
psql -p 5555 -U obertruper -d bot_trading_v3 -c "SELECT version();"

# Миграции Alembic
alembic upgrade head                          # Применить все
alembic revision --autogenerate -m "add_xxx"  # Новая миграция
alembic downgrade -1                          # Откатить последнюю

# Прямая работа с БД через asyncpg
python3 -c "
from database.connections.postgres import AsyncPGPool
import asyncio
asyncio.run(AsyncPGPool.fetch('SELECT COUNT(*) FROM orders'))
"
```

### Отладка проблем

```bash
# Смотреть логи в реальном времени
tail -f data/logs/trading.log | grep ERROR

# Проверить использование портов
lsof -i :8080  # API
lsof -i :5173  # Frontend
lsof -i :5555  # PostgreSQL

# Мониторинг производительности
htop -p $(pgrep -f "python.*main.py")
```

## 🚀 Unified Launcher

`unified_launcher.py` управляет всеми компонентами системы с автоперезапуском и health checks.

**Особенности**: Process isolation, автоперезапуск (5 попыток), мониторинг ресурсов, правильный venv

**URLs после запуска**:

- Frontend: <http://localhost:5173>
- API: <http://localhost:8080>
- API Docs: <http://localhost:8080/api/docs>

### 🧠 ML Trading Flow (РАБОТАЕТ и ИСПРАВЛЕН!)

```
1. ML Manager загружает UnifiedPatchTST модель (GPU RTX 5090)
2. ML Signal Processor генерирует УНИКАЛЬНЫЕ сигналы каждую минуту
3. Signal Scheduler отправляет в AI Signal Generator
4. AI Signal Generator эмитит в Trading Engine
5. Trading Engine конвертирует и добавляет в очередь
6. Signal Processor создает ордера с risk management
7. Order Manager отправляет на биржи
```

**Тестирование ML**:

- Проверка flow: `python test_ml_flow_simple.py`
- Проверка уникальности: `python debug_unique_predictions.py`
- Мониторинг: `tail -f ./data/logs/bot_trading_*.log | grep -E "signal_type|returns_15m"`

## 📡 MCP серверы и Claude Code хуки

### Активные MCP серверы

- **filesystem** - работа с файлами проекта
- **postgres** - БД на порту 5555
- **puppeteer** - браузерная автоматизация
- **sequential-thinking** - сложные рассуждения
- **memory** - контекст между сессиями
- **github** - работа с репозиторием
- **sonarqube** - качество кода

### Claude Code хуки (.claude/hooks.json)

- **PreToolUse**: защита .env, логирование bash команд
- **PostToolUse**: автоформатирование (black, ruff), напоминания о тестах

```bash
claude-code mcp list      # Проверить MCP серверы
claude-code test-hooks    # Тестировать хуки
```

## 💡 Архитектурные принципы

1. **Async-first**: Все I/O операции через async/await
2. **Fail-safe**: Graceful degradation при сбоях бирж
3. **Security-by-default**: Секреты только в .env, валидация входных данных
4. **Observable**: Структурированные логи (structlog), Prometheus метрики
5. **Testable**: Dependency injection, моки для внешних сервисов

## 🔧 Технологический стек

**Backend**: Python 3.8+, FastAPI, asyncpg, SQLAlchemy 2.0, ccxt (7 бирж), aiohttp, Redis
**ML/AI**: PyTorch (UnifiedPatchTST), XGBoost, anthropic SDK, cross-verification (3 AI)
**Monitoring**: Prometheus:9090, Grafana:3000, Sentry, structlog
**Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Zustand
**Performance**: 1000+ сигналов/сек, <50ms API, 240+ ML признаков

## 🔥 Частые проблемы

**Import errors**: `source venv/bin/activate` + `pip install -r requirements.txt`

**DB connection failed**: Проверь PostgreSQL на 5555: `psql -p 5555 -U obertruper -d bot_trading_v3`

**WebSocket disconnects**: Увеличь таймауты в `config/system.yaml`

**"position idx not match position mode"**: Несоответствие настроек hedge mode

- Проверь `trading.hedge_mode` в `config/system.yaml` (должно быть `true` для hedge mode)
- Убедись что на бирже включен hedge mode (не one-way mode)
- Position indices: 0 = one-way, 1 = buy/long, 2 = sell/short
- Решение: установи `hedge_mode: true` и перезапусти систему

**ML выдает одинаковые предсказания**: Проблема с кэшированием

- Перезапусти систему: `pkill -f "python.*unified_launcher" && python3 unified_launcher.py`
- Проверь уникальность: `tail -f ./data/logs/bot_trading_*.log | grep "returns_15m" | uniq`
- Отладка: `python3 debug_unique_predictions.py`

## ⚡ Правила разработки

1. **Обязательно async/await** для всех I/O операций
2. **Type hints везде**: `def process_signal(signal: Signal) -> Order:`
3. **Тесты для новых функций**: минимум 80% покрытие
4. **Перед коммитом**: `black . && ruff check --fix . && mypy .`
5. **AI агенты**: используй для code review и генерации тестов

## 📁 Структура проекта

```
BOT_AI_V3/
├── unified_launcher.py    # 🚀 Главная точка входа
├── main.py               # Торговое ядро
├── .env                  # Секреты (НЕ коммитить!)
├── config/               # YAML конфигурации
│   ├── ml/ml_config.yaml # ML параметры (240+ features)
│   └── system.yaml       # Системные настройки
├── core/                 # Основная бизнес-логика
│   └── system/          # orchestrator.py, process_manager.py
├── trading/             # Торговая логика
│   └── engine.py        # TradingEngine (главный класс)
├── strategies/          # Торговые стратегии
├── exchanges/           # Интеграции с биржами (7 бирж)
├── ml/                  # ML компоненты
│   └── logic/          # patchtst_model.py, feature_engineering.py
├── database/            # БД слой
│   └── connections/    # postgres.py (async/sync pools)
├── web/                 # API и Frontend
├── data/               # Runtime данные
│   └── logs/          # trading.log, error.log
└── tests/              # Тесты (pytest)

## 🔥 Частые проблемы

**Import errors**: `source venv/bin/activate` + `pip install -r requirements.txt`

**DB connection failed**: Проверь PostgreSQL на 5555: `psql -p 5555 -U obertruper -d bot_trading_v3`

**WebSocket disconnects**: Увеличь таймауты в `config/system.yaml`

## 💾 База данных

### Основные таблицы
- **orders**: статусы (pending, open, filled, cancelled)
- **trades**: исполненные сделки с PnL
- **signals**: торговые сигналы
- **raw_market_data**: OHLCV данные
- **processed_market_data**: ML features (240+)

### Примеры работы с БД

```python
# Async подключение (предпочтительно)
from database.connections.postgres import AsyncPGPool
trades = await AsyncPGPool.fetch("SELECT * FROM trades WHERE symbol=$1", "BTCUSDT")

# SQLAlchemy async
from database.connections import get_async_db
async with get_async_db() as db:
    result = await db.execute(select(Order).where(Order.status == "open"))
```

## 🔑 Переменные окружения (.env)

```bash
# PostgreSQL (КРИТИЧНО: порт 5555!)
PGPORT=5555
PGUSER=obertruper
PGDATABASE=bot_trading_v3

# Минимум одна биржа для работы
BYBIT_API_KEY=xxx
BYBIT_API_SECRET=xxx

# AI (опционально)
CLAUDE_API_KEY=xxx
GITHUB_TOKEN=xxx  # Для MCP

# Торговые настройки
DEFAULT_LEVERAGE=1
MAX_POSITION_SIZE=1000
RISK_LIMIT_PERCENTAGE=2
```

## 🧠 ML система (UnifiedPatchTST)

**Модель**: PyTorch Transformer, 240 входов → 20 выходов (направления, уровни, риски)
**Контекст**: 96 точек (24 часа при 15-мин интервалах)
**Признаки**: 240+ (технические индикаторы, микроструктура, временные)
**Производительность**: F1=0.414, предсказания каждую минуту для 50+ пар

### Ключевые ML файлы

- `ml/logic/patchtst_model.py` - архитектура модели
- `ml/logic/feature_engineering.py` - генерация 240+ признаков
- `config/ml/ml_config.yaml` - параметры обучения и торговли
- `docs/ML_SIGNAL_EVALUATION_SYSTEM.md` - 📚 подробное описание системы оценки
- `docs/ML_TUNING_GUIDE.md` - 🎛️ руководство по настройке параметров

### Запуск ML торговли

```bash
python3 unified_launcher.py --mode=ml  # Торговля с ML
```

## 🤖 Работа с Claude Code агентами

### ✅ ML интеграция ЗАВЕРШЕНА и ИСПРАВЛЕНА

Успешно реализована полная ML система генерации торговых сигналов:

- ✅ UnifiedPatchTST модель с GPU оптимизацией (RTX 5090)
- ✅ Feature Engineering с 240+ индикаторами real-time
- ✅ Signal flow: ML → AISignalGenerator → TradingEngine → Orders
- ✅ Thread-safe репозитории (SignalRepository, TradeRepository)
- ✅ Автоматическая генерация сигналов каждую минуту
- ✅ Risk management интегрирован в создание ордеров
- ✅ **ИСПРАВЛЕНО (08.11.2025)**: Уникальные предсказания для каждой криптовалюты
  - Исправлено кэширование в `ml_signal_processor.py`
  - Добавлен хэш данных в ключ кэша
  - TTL кэша уменьшен с 15 до 5 минут
  - Теперь каждая монета получает индивидуальные предсказания

### Использование агентов через Task tool

Claude Code автоматически выберет нужного агента на основе контекста. Используй Task tool для сложных задач:

```python
# Пример вызова агента
Task(
    description="Оптимизировать ML торговлю",
    prompt="Улучши производительность ML предсказаний для 50+ торговых пар",
    subagent_type="general-purpose"  # Всегда используй general-purpose
)
```

### Доступные специализированные агенты

**Торговля**: trading-core-expert, strategy-optimizer, risk-analyzer, exchange-specialist
**Разработка**: code-architect, feature-developer, debug-specialist, refactor-expert
**Инфраструктура**: database-architect, performance-tuner, security-guardian, api-developer
**ML/AI**: ml-optimizer, test-architect, docs-maintainer, agent-manager

Агенты автоматически используют TodoWrite для планирования и интегрированы с MCP хуками.

## 📊 Версия и статус

**Версия**: 3.0.0-beta
**Статус**: Active Development - ML интеграция завершена 🎉
**Последнее обновление**: 8 августа 2025

---

*Подробности реализации и исторические изменения см. в документации проекта*
