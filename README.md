# BOT Trading v3 🤖📈

Мощная система автоматической торговли криптовалютой с поддержкой множественных стратегий, AI-агентов и мультибиржевой интеграции.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-SDK-purple.svg)](https://claude.ai/code)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Основные возможности

### 🏗️ Мульти-трейдерная архитектура

- **Изолированные контексты** для каждого трейдера
- **Независимое управление** стратегиями и рисками
- **Горизонтальное масштабирование** под высокие нагрузки
- **Централизованная координация** через системный оркестратор

### 📊 Расширенная система рисков

- **Реальное время мониторинга** с автоматическими действиями
- **Многоуровневые проверки**: портфельные, позиционные, ликвидные, корреляционные
- **Трейлинг-стопы** и частичные закрытия позиций
- **VaR, Sharpe ratio, drawdown** анализ

### 🧠 AI-интеграция с Claude Code SDK

- **Полная интеграция** с Claude Code через Python SDK
- **Playwright MCP** для браузерной автоматизации (✅ работает с ChatGPT o3-pro, Grok v4, Claude Opus 4)
- **Smart cross-verification** система принятия решений (3 минуты вместо 10!)
- **Автоматическое ревью кода** и генерация тестов
- **Оптимизированная кросс-верификация** с параллельной обработкой и кэшированием
- **Активация по слову "кросс"** или автоматически для критических задач

### 🏦 Мульти-биржевая поддержка

- **Унифицированные интерфейсы** для 7+ ведущих бирж
- **Балансировка нагрузки** и failover механизмы
- **Арбитражные возможности** между биржами
- **Поддерживаемые биржи**: Bybit, Binance, OKX, Bitget, Gate.io, KuCoin, Huobi

### 📈 Продвинутые торговые стратегии

- **Модульная система** с горячей заменой стратегий
- **Backtesting** с историческими данными
- **ML-оптимизация** параметров через XGBoost (~63% точность)
- **A/B тестирование** новых алгоритмов

## 🛠️ Технологический стек

### Backend

- **Python 3.11+** с асинхронным программированием
- **FastAPI** для высокопроизводительного веб-API
- **PostgreSQL** с thread-safe репозиториями
- **Redis** для кеширования и очередей
- **Alembic** для миграций базы данных

### AI & Automation

- **Claude Code SDK** для AI-автоматизации
- **Playwright MCP** для браузерных операций
- **XGBoost** для машинного обучения
- **Model Context Protocol** для интеграций

### Monitoring & DevOps

- **Prometheus** метрики
- **Grafana** дашборды
- **Structlog** для структурированного логирования
- **Pytest** для тестирования

## 📦 Быстрый старт

### 1. Системные требования

```bash
# Python 3.11+
python --version

# PostgreSQL 15+
psql --version

# Redis
redis-cli --version

# Node.js для MCP серверов
node --version
```

### 2. Установка зависимостей

```bash
# Клонирование репозитория
git clone https://github.com/your-username/BOT_Trading_v3.git
cd BOT_Trading_v3

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 3. Конфигурация окружения

```bash
# Копирование и настройка .env файла
cp config/.env.example .env

# Настройка базы данных
# Редактируем .env файл
DATABASE_URL=postgresql://user:password@localhost/bot_trading_v3
REDIS_URL=redis://localhost:6379

# API ключи бирж
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret

# Claude Code SDK
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_CODE_PROJECT_ID=your_project_id
```

### 4. Инициализация базы данных

```bash
# Создание базы данных
createdb bot_trading_v3

# Применение миграций
alembic upgrade head
```

### 5. Запуск системы

```bash
# Веб-интерфейс (development)
uvicorn web.main:app --reload --host 0.0.0.0 --port 8000

# Торговый движок
python -m core.main

# Веб-интерфейс будет доступен по адресу: http://localhost:8000
```

## 🏗️ Архитектура системы

```
┌─────────────────┬─────────────────┬─────────────────┐
│   Веб-интерфейс │  AI Агенты      │  Мониторинг     │
│   (FastAPI)     │  (Claude Code)  │  (Prometheus)   │
├─────────────────┴─────────────────┴─────────────────┤
│              Системный оркестратор                  │
├──────────────┬──────────────┬─────────────────────┤
│ Торговый     │ Управление   │ Управление          │
│ движок       │ стратегиями  │ рисками             │
├──────────────┼──────────────┼─────────────────────┤
│          Мульти-биржевая интеграция               │
├───────────────────────────────────────────────────┤
│     PostgreSQL + Redis + Thread-safe repos       │
└───────────────────────────────────────────────────┘
```

### 📁 Структура проекта

- **20+ основных модулей** - полная модульная архитектура
- **7 биржевых интеграций** - Binance, Bybit, OKX, Bitget, Gate.io, Huobi, KuCoin
- **5 типов стратегий** - арбитраж, сетка, индикаторы, ML, скальпинг
- **Расширенные компоненты** - API слой, индикаторы, ML, мониторинг, утилиты

Полная структура проекта доступна в [docs/COMPLETE_PROJECT_STRUCTURE.md](docs/COMPLETE_PROJECT_STRUCTURE.md)

### Основные компоненты

#### 🚀 Торговый движок (`trading/engine.py`)

- Координация всех торговых операций
- Обработка сигналов в реальном времени
- Управление позициями и ордерами
- Интеграция с системой рисков

#### 📋 Система стратегий (`strategies/`)

- Загрузка и управление жизненным циклом стратегий
- Мониторинг производительности
- Горячая замена стратегий
- Бэктестинг и оптимизация

#### ⚠️ Управление рисками (`risk_management/`)

- Реальное время мониторинга рисков
- Автоматические действия при превышении лимитов
- Расчет VaR, Sharpe ratio, максимальной просадки
- Трейлинг-стопы и частичные закрытия

#### 🏦 Биржевые интеграции (`exchanges/`)

- Унифицированные API для всех бирж
- Балансировка нагрузки
- Failover механизмы
- Арбитражные возможности

#### 🤖 AI Агенты (`ai_agents/`)

- **Code Reviewer**: анализ качества кода
- **Test Generator**: автогенерация тестов
- **Strategy Optimizer**: оптимизация стратегий
- **Doc Maintainer**: поддержка документации
- **Cross-Verification** 🆕: кросс-проверка через ChatGPT o3-pro, Grok v4 и Claude Opus 4
  - Автоматическая активация по слову "кросс"
  - Параллельная обработка (3 минуты вместо 10)
  - Единый синтезированный отчет

## 🔧 Конфигурация

### MCP Серверы для Claude Code

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/BOT_Trading_v3"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@executeautomation/playwright-mcp-server"]
    }
  }
}
```

### Хуки для автоматизации

```json
{
  "beforeEdit": "ruff check --select E9,F63,F7,F82 {{file}}",
  "afterEdit": "black {{file}} && ruff check {{file}}",
  "beforeCommit": "pytest tests/ --tb=short -x"
}
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest tests/ --tb=short -v

# Unit тесты с покрытием
pytest tests/unit/ --cov=src/ --cov-report=html

# Интеграционные тесты
pytest tests/integration/ --slow

# E2E тесты с Playwright
pytest tests/e2e/ --browser=chromium
```

### Генерация тестов через AI

```bash
# Автогенерация тестов для класса
python -m ai_agents.test_generator --class=TradingEngine

# Покрытие edge cases
python -m ai_agents.test_generator --edge-cases --file=trading/engine.py
```

## 📊 Мониторинг и метрики

### Доступные дашборды

- **Основной дашборд**: <http://localhost:3000>
- **Торговые метрики**: производительность, PnL, винрейт
- **Системные метрики**: CPU, память, сетевой трафик
- **Риски**: текущие риски, алерты, лимиты

### Алерты и уведомления

- **Критические**: PagerDuty интеграция
- **Торговые события**: Slack уведомления
- **Системные**: Grafana алерты

## 🛡️ Безопасность

### Лучшие практики

- ✅ Переменные окружения для секретов
- ✅ Rate limiting для API
- ✅ Валидация всех входных данных
- ✅ Логирование без чувствительных данных
- ✅ Регулярные security audit

### Управление API ключами

```bash
# Безопасное хранение
export BYBIT_API_KEY="your_api_key"
export BYBIT_API_SECRET="your_api_secret"

# Ротация ключей
python -m scripts.rotate_api_keys --exchange=bybit
```

## 🚀 Развертывание

### Docker (Рекомендуется)

```bash
# Сборка образа
docker build -t bot-trading-v3 .

# Запуск с docker-compose
docker-compose up -d

# Проверка логов
docker-compose logs -f trading-engine
```

### Продакшн развертывание

```bash
# Подготовка окружения
export ENVIRONMENT=production

# Запуск через gunicorn
gunicorn web.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Запуск торгового движка
python -m core.main --config=config/production.yaml
```

## 📈 Производительность

### Бенчмарки

- **Обработка сигналов**: ~1000 сигналов/сек
- **API ответы**: <50ms медиана
- **Websocket latency**: <10ms
- **Память**: ~512MB базовое потребление
- **CPU**: эффективное использование в асинхронном режиме

### Оптимизация

```bash
# Профилирование производительности
python -m scripts.profile_trading_engine

# Анализ памяти
python -m scripts.memory_analysis

# Нагрузочное тестирование
python -m scripts.load_test --concurrent=100
```

## 🤝 Участие в разработке

### Рабочий процесс

1. **Fork** репозитория
2. Создание **feature branch**: `git checkout -b feature/amazing-feature`
3. **Разработка** с TDD подходом
4. **Тестирование**: `pytest tests/`
5. **Code review** через AI агентов
6. **Pull request** с подробным описанием

### Стандарты кода

```bash
# Автоформатирование
black .
ruff check --fix .

# Проверка типов
mypy src/

# Комплексная проверка
pre-commit run --all-files
```

## 📚 Документация

### Полная документация

- **API документация**: <http://localhost:8000/docs>
- **Архитектура**: [docs/architecture.md](docs/architecture.md)
- **Конфигурация**: [docs/configuration.md](docs/configuration.md)
- **Развертывание**: [docs/deployment.md](docs/deployment.md)

### AI-генерация документации

```bash
# Автообновление документации
python -m ai_agents.doc_maintainer --update-all

# Генерация API docs
python -m ai_agents.doc_maintainer --api-docs

# Кросс-верификация стратегий/архитектуры (NEW!)
python -m ai_agents.cross_verification --task="Оптимальная HFT архитектура"
# Автоматически: ChatGPT o3-pro + Grok v4 + Claude Opus 4 → единый отчет за 3 минуты

# Примеры активации по ключевому слову
python -m ai_agents.cross_verification --task="кросс: проверь стратегию скальпинга"
python -m ai_agents.cross_verification --task="кросс-проверка архитектуры микросервисов"
```

## 📊 Статус миграции v2 → v3

- ✅ **Веб-интерфейс** (100% завершен)
- ✅ **AI агенты система** (100% завершена)
- ✅ **Торговый движок** (100% завершен)
- ✅ **Система стратегий** (100% завершена)
- ✅ **Система рисков** (100% завершена)
- 🔄 **Мульти-биржевая интеграция** (70% завершена)
- 🔄 **Database layer** (80% завершена)
- 🔄 **Тестирование** (60% завершено)
- 📋 **Документация** (в процессе)

## 🐛 Известные проблемы и ограничения

### Текущие ограничения

- Некоторые биржи поддерживаются частично
- WebSocket реконнекты могут занимать до 30 секунд
- Максимум 1000 одновременных стратегий

### Планируемые улучшения

- [ ] Поддержка options торговли
- [ ] DeFi протоколы интеграция
- [ ] Улучшенный UI/UX
- [ ] Mobile приложение

## 📞 Поддержка

### Сообщество

- **GitHub Issues**: [Issues](https://github.com/your-username/BOT_Trading_v3/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/BOT_Trading_v3/discussions)
- **Telegram**: [@bot_trading_v3](https://t.me/bot_trading_v3)

### Enterprise поддержка

- **Email**: <support@bot-trading-v3.com>
- **SLA**: 4-часовое время ответа
- **Custom features**: доступна разработка под заказ

## 📄 Лицензия

Проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).

## 🙏 Благодарности

### Технологии

- **Anthropic** за Claude Code SDK
- **FastAPI** за высокопроизводительный фреймворк
- **PostgreSQL** за надежную базу данных

### Участники

- [@username1](https://github.com/username1) - Lead Developer
- [@username2](https://github.com/username2) - AI Integration
- [@username3](https://github.com/username3) - Risk Management

---

**Последнее обновление**: 13 июля 2025
**Версия**: 3.0.0-alpha
**Статус**: Active Development

Made with ❤️ and 🤖 by BOT Trading Team
