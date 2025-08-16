# Архитектура проекта BOT_AI_V3

## Граф структуры системы

```mermaid
flowchart TB
    %% Стили для разных типов компонентов
    classDef rootStyle fill:#ff6b6b,stroke:#333,stroke-width:4px,color:#fff
    classDef entryStyle fill:#4ecdc4,stroke:#333,stroke-width:2px,color:#fff
    classDef coreStyle fill:#45b7d1,stroke:#333,stroke-width:2px,color:#fff
    classDef mlStyle fill:#96ceb4,stroke:#333,stroke-width:2px,color:#fff
    classDef dataStyle fill:#ffeaa7,stroke:#333,stroke-width:2px,color:#333
    classDef apiStyle fill:#dfe6e9,stroke:#333,stroke-width:2px,color:#333
    classDef exchangeStyle fill:#a29bfe,stroke:#333,stroke-width:2px,color:#fff
    classDef monitorStyle fill:#fd79a8,stroke:#333,stroke-width:2px,color:#fff

    %% Основные компоненты
    BOT_AI_V3["BOT_AI_V3<br/>Root System<br/>673 files, 207K+ LOC"]:::rootStyle
    UnifiedLauncher["UnifiedLauncher<br/>Entry Point<br/>unified_launcher.py"]:::entryStyle
    SystemOrchestrator["SystemOrchestrator<br/>Core Component<br/>orchestrator.py"]:::coreStyle

    %% Trading компоненты
    TradingEngine["TradingEngine<br/>Trading Core<br/>engine.py:597"]:::coreStyle
    OrderManager["OrderManager<br/>Order Management<br/>order_manager.py"]:::coreStyle
    RiskManager["RiskManager<br/>Risk Control<br/>5x leverage, 2% risk"]:::coreStyle
    SignalGenerator["SignalGenerator<br/>Signal Generation<br/>ai_signal_generator.py"]:::coreStyle

    %% ML компоненты
    MLManager["MLManager<br/>ML System<br/>UnifiedPatchTST"]:::mlStyle
    MLSignalProcessor["MLSignalProcessor<br/>ML Processing<br/>Unique predictions/min"]:::mlStyle
    FeatureEngineering["FeatureEngineering<br/>ML Features<br/>240+ indicators"]:::mlStyle

    %% Data компоненты
    DataManager["DataManager<br/>Data Management<br/>Real-time updates"]:::dataStyle
    PostgreSQL[("PostgreSQL<br/>Database<br/>Port 5555")]:::dataStyle

    %% Exchange компоненты
    ExchangeManager["ExchangeManager<br/>7 Exchanges<br/>Bybit, Binance, OKX..."]:::exchangeStyle

    %% Web компоненты
    WebAPI["WebAPI<br/>REST API<br/>Port 8080"]:::apiStyle
    Frontend["Frontend<br/>React + TS<br/>Port 5173"]:::apiStyle

    %% Utility компоненты
    ConfigManager["ConfigManager<br/>Configuration<br/>YAML configs"]:::monitorStyle
    HealthMonitor["HealthMonitor<br/>Monitoring<br/>health_monitor.py"]:::monitorStyle
    AlembicMigrations["AlembicMigrations<br/>DB Migrations<br/>alembic/"]:::dataStyle

    %% Связи - Entry flow
    BOT_AI_V3 -->|entry point| UnifiedLauncher
    UnifiedLauncher -->|starts| SystemOrchestrator
    UnifiedLauncher -->|launches| WebAPI
    UnifiedLauncher -->|launches| Frontend

    %% Связи - Core orchestration
    SystemOrchestrator -->|coordinates| TradingEngine
    SystemOrchestrator -->|manages| MLManager
    SystemOrchestrator -->|controls| DataManager
    SystemOrchestrator -->|monitors with| HealthMonitor

    %% Связи - Trading flow
    TradingEngine -->|receives signals| SignalGenerator
    TradingEngine -->|validates with| RiskManager
    TradingEngine -->|creates orders| OrderManager
    RiskManager -->|approves| OrderManager
    OrderManager -->|executes on| ExchangeManager

    %% Связи - ML flow
    MLManager -->|uses features| FeatureEngineering
    MLManager -->|sends predictions| MLSignalProcessor
    MLSignalProcessor -->|provides signals| SignalGenerator
    FeatureEngineering -->|processes data| DataManager

    %% Связи - Data flow
    DataManager -->|fetches from| ExchangeManager
    DataManager -->|stores in| PostgreSQL
    OrderManager -->|stores orders| PostgreSQL
    SignalGenerator -->|saves signals| PostgreSQL
    ExchangeManager -->|logs trades| PostgreSQL
    HealthMonitor -->|logs metrics| PostgreSQL

    %% Связи - Web flow
    Frontend -->|connects to| WebAPI
    WebAPI -->|communicates| SystemOrchestrator
    WebAPI -->|queries| PostgreSQL

    %% Связи - Configuration
    ConfigManager -->|configures| SystemOrchestrator
    ConfigManager -->|provides config| TradingEngine
    AlembicMigrations -->|migrates| PostgreSQL
```

## Описание компонентов

### 🔴 Root System

- **BOT_AI_V3**: Главная система алгоритмической торговли криптовалютами
  - 673 файла, 207K+ строк кода
  - Python 3.8+, PostgreSQL 15+
  - Поддержка 7 бирж
  - ML модель UnifiedPatchTST с 240+ признаками

### 🟢 Entry Point & Orchestration

- **UnifiedLauncher**: Точка входа системы (unified_launcher.py)
  - Запуск всех процессов
  - Управление режимами (core, api, ml)

- **SystemOrchestrator**: Координация компонентов (core/system/orchestrator.py)
  - Управление жизненным циклом
  - Синхронизация модулей

### 🔵 Trading Core

- **TradingEngine**: Основная торговая логика (trading/engine.py:597)
  - Обработка сигналов
  - Управление ордерами

- **OrderManager**: Управление ордерами (trading/orders/order_manager.py)
  - Создание и исполнение ордеров
  - Интеграция SL/TP
  - Hedge mode

- **RiskManager**: Контроль рисков (risk_management/manager.py)
  - Кредитное плечо 5x
  - Лимит риска 2%
  - Расчет размера позиций

### 🟣 ML System

- **MLManager**: Управление ML моделями (ml/ml_manager.py)
  - UnifiedPatchTST модель
  - GPU оптимизация (RTX 5090)

- **MLSignalProcessor**: Обработка предсказаний (ml/ml_signal_processor.py)
  - Уникальные предсказания/минута
  - Кэширование с TTL 5 минут

- **FeatureEngineering**: Инженерия признаков (ml/logic/feature_engineering_v2.py)
  - 240+ технических индикаторов
  - Обработка OHLCV данных

### 🟡 Data Layer

- **DataManager**: Управление данными (core/system/data_manager.py)
  - Real-time обновления
  - Кэширование

- **PostgreSQL**: База данных (порт 5555)
  - Хранение ордеров, сделок, сигналов
  - ML предсказания
  - Рыночные данные

### 🟠 Exchange Integration

- **ExchangeManager**: Интеграция с биржами (exchanges/exchange_manager.py)
  - 7 бирж: Bybit, Binance, OKX, Gate.io, KuCoin, HTX, BingX
  - API и WebSocket подключения

### ⚪ Web Interface

- **WebAPI**: REST API (web/api/main.py)
  - Порт 8080
  - WebSocket для real-time
  - API документация /api/docs

- **Frontend**: Пользовательский интерфейс (web/frontend/)
  - React + TypeScript
  - Порт 5173
  - Real-time мониторинг

### 🔧 Utilities

- **ConfigManager**: Управление конфигурацией
  - YAML конфигурации
  - Environment переменные

- **HealthMonitor**: Мониторинг системы
  - Проверка компонентов
  - Метрики производительности

- **AlembicMigrations**: Миграции БД
  - Версионирование схемы
  - Автоматические миграции

## Поток данных

1. **Запуск**: BOT_AI_V3 → UnifiedLauncher → SystemOrchestrator
2. **Сбор данных**: ExchangeManager → DataManager → PostgreSQL
3. **ML обработка**: DataManager → FeatureEngineering → MLManager → MLSignalProcessor
4. **Генерация сигналов**: MLSignalProcessor → SignalGenerator → TradingEngine
5. **Исполнение**: TradingEngine → RiskManager → OrderManager → ExchangeManager
6. **Мониторинг**: HealthMonitor → PostgreSQL, WebAPI → Frontend

## Ключевые особенности

- **Масштаб**: 673 файла, 207K+ строк кода
- **Производительность**: GPU оптимизация, async операции
- **Надежность**: Risk management, health monitoring
- **Гибкость**: 7 бирж, 50+ торговых пар
- **ML**: UnifiedPatchTST модель, 240+ признаков
- **Real-time**: WebSocket подключения, live мониторинг
