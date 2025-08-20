# Changelog

All notable changes to BOT_AI_V3 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.1] - 2025-08-20

### 🔄 Критические исправления ML системы

#### Fixed

- **Интерпретация классов направлений ML**: Исправлена критическая ошибка в интерпретации выходных классов модели
  - **До**: 0=DOWN, 1=FLAT, 2=UP (неправильная интерпретация)
  - **После**: 0=LONG, 1=SHORT, 2=FLAT (правильная интерпретация согласно обучающему проекту)
  - Файлы: `ml/model_adapter.py`, `ml/logic/patchtst_model.py`, `unified_launcher.py`

- **Уникальность ML предсказаний**: Каждый символ теперь получает уникальные предсказания
  - Добавлен hash данных в ключ кэша: `{exchange}:{symbol}:{time}:{data_hash}`
  - Исправлена проблема одинаковых предсказаний для разных символов
  - Файл: `ml/ml_signal_processor.py`

- **Система кэширования ML**: Улучшенная система с автоматической очисткой
  - TTL кэша: 5 минут (300 секунд)
  - Максимальный размер: 1000 записей
  - Автоматическая очистка по времени и размеру
  - Статистика попаданий/промахов кэша

- **Отображение статуса ML**: Корректное отображение в unified_launcher при интеграции с Core System
  - Исправлена логика определения статуса "Запущен/Остановлен"

#### Added

- **Новые React компоненты для визуализации ML метрик**:
  - `MLCacheMetrics.tsx` - мониторинг эффективности кэша
  - `MLDirectionDistribution.tsx` - визуализация распределения LONG/SHORT/FLAT
  - Интеграция в главный дашборд (`Dashboard.tsx`)

- **API эндпоинты для ML метрик**:
  - `GET /api/ml/cache-stats` - статистика кэша
  - `GET /api/ml/direction-stats` - распределение направлений
  - Модели: `MLCacheMetricsResponse`, `MLDirectionStatsResponse`

- **Новые конфигурационные параметры**:
  ```yaml
  model:
    direction_confidence_threshold: 0.5  # Порог уверенности для классов
  cache:
    ttl_seconds: 300
    max_size: 1000
    cleanup_interval: 60
    enable_stats: true
  ```

- **Документация исправлений**:
  - `docs/ML_DIRECTION_CLASSES_FIX.md` - детальное описание исправления классов
  - `docs/ML_CACHE_SYSTEM.md` - документация системы кэширования

#### Changed

- **Frontend компоненты**: Обновлены для отображения LONG/SHORT вместо buy/sell
  - Файл: `web/frontend/src/components/dashboard/MLSignalsPanel.tsx`
  - Поддержка обратной совместимости с buy/sell сигналами

- **Совместимость выходов модели**: Полное соответствие с обучающим проектом
  - Модель возвращает направление классы (0,1,2) вместо усредненных скоров
  - Исправлена функция `_convert_predictions_to_signal`

### 🎯 Влияние исправлений

- **Точность торговых решений**: Устранена инверсия торговых сигналов
- **Уникальность предсказаний**: Каждый символ получает персонализированные ML предсказания  
- **Производительность кэша**: Оптимизированное использование памяти и времени отклика
- **Мониторинг системы**: Полная визуализация работы ML компонентов

## [3.1.0] - 2025-01-14

### Added

- Complete Feature Engineering v2.0 system with 240 ML features
- Comprehensive documentation for Feature Engineering and ML System
- Migration guide for upgrading from v1.0 to v2.0
- Automatic feature trimming to 240 for ML compatibility
- Method stubs for logger compatibility (start_stage, end_stage)
- **ML Predictions Logging System**:
  - Detailed logging of all ML model inputs and outputs
  - PostgreSQL tables for storing predictions and feature importance
  - Real-time prediction tracking with performance metrics
  - Analytics script for analyzing prediction accuracy
  - Batch saving optimization for high-throughput scenarios

### Changed

- Feature engineering now independent of configuration
- All technical indicators created with default parameters
- Improved feature naming consistency (ichimoku_tenkan, keltner_upper_20, etc.)
- Updated realtime_indicator_calculator.py to filter target variables
- Enhanced ML signal processing with better caching

### Fixed

- Feature count mismatch errors (273 → 240 automatic trimming)
- Missing indicators (OBV, Ichimoku, Keltner, Donchian)
- Indentation errors in Bollinger Bands calculation
- Target variable leakage in ML features
- Logger compatibility issues with original code

### Technical Details

- **Feature Categories**:
  - Basic Features: 12
  - Technical Indicators: 52
  - Microstructure: 15
  - Rally Detection: 42
  - Signal Quality: 21
  - Futures-Specific: 15
  - ML-Optimized: 30+
  - Temporal: 16
  - Cross-Asset: 5
  - **Total**: 273 (240 features + 33 targets)

## [3.0.0] - 2025-01-10

### Added

- Unified launcher system for all components
- ML trading with UnifiedPatchTST model
- PostgreSQL on port 5555 support
- 7 exchange integrations (Bybit, Binance, OKX, Gate.io, KuCoin, HTX, BingX)
- Web interface and API server

### Changed

- Complete project restructuring (178 files → organized structure)
- Leverage fixed at 5x for all positions
- Stop Loss/Take Profit integration at order creation

### Fixed

- Leverage issues (was 10x, now correctly 5x)
- SL/TP not being set on positions
- File organization and structure

## [2.0.0] - 2024-12-01

### Added

- Machine Learning predictions system
- Advanced risk management
- Multi-symbol support (50+ pairs)
- Real-time WebSocket connections

### Changed

- Migrated from synchronous to asynchronous architecture
- Updated to Bybit API v5

## [1.0.0] - 2024-10-01

### Added

- Initial release
- Basic trading functionality
- Simple technical indicators
- Single exchange support (Bybit)

---

## Feature Engineering Versions

### v2.0 (Current)

- 240 ML features + 33 targets
- No configuration dependency
- Automatic feature management

### v1.0 (Legacy)

- Variable feature count (200-300)
- Configuration-dependent
- Manual feature selection

## Model Versions

### UnifiedPatchTST v1.0 (Current)

- Transformer-based architecture
- 96 timesteps × 240 features input
- 20 predictions output
- ~2M parameters

---

*For detailed migration instructions, see [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md)*
