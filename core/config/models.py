#!/usr/bin/env python3
"""Pydantic модели для валидации и типизации конфигурации системы BOT_AI_V3.

Обеспечивает строгую типизацию и валидацию всех параметров конфигурации
с поддержкой переменных окружения и значений по умолчанию.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class Environment(str, Enum):
    """Окружения запуска системы."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Уровни логирования."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OrderType(str, Enum):
    """Типы ордеров."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class ExchangeName(str, Enum):
    """Поддерживаемые биржи."""

    BYBIT = "bybit"
    BINANCE = "binance"
    OKX = "okx"
    GATEIO = "gateio"
    KUCOIN = "kucoin"
    HTX = "htx"
    BINGX = "bingx"


# ============= Системные настройки =============


class SystemLimits(BaseModel):
    """Лимиты системы."""

    max_traders: int = Field(default=10, ge=1, le=100)
    max_concurrent_trades: int = Field(default=50, ge=1, le=1000)
    max_memory_usage_mb: int = Field(default=2048, ge=512, le=32768)
    max_cpu_usage_percent: int = Field(default=80, ge=10, le=100)


class SystemPerformance(BaseModel):
    """Настройки производительности."""

    worker_threads: int = Field(default=4, ge=1, le=32)
    async_pool_size: int = Field(default=100, ge=10, le=1000)
    connection_pool_size: int = Field(default=20, ge=5, le=100)
    cache_size_mb: int = Field(default=512, ge=64, le=4096)


class WebInterface(BaseModel):
    """Настройки веб-интерфейса."""

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8083, ge=1024, le=65535)
    cors_enabled: bool = Field(default=True)


class SystemSettings(BaseModel):
    """Основные системные настройки."""

    name: str = Field(default="BOT_Trading_v3")
    version: str = Field(default="3.0.0")
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    limits: SystemLimits = Field(default_factory=SystemLimits)
    performance: SystemPerformance = Field(default_factory=SystemPerformance)
    web_interface: WebInterface = Field(default_factory=WebInterface)


# ============= База данных =============


class DatabasePool(BaseModel):
    """Настройки пула соединений БД."""

    min_connections: int = Field(default=5, ge=1, le=50)
    max_connections: int = Field(default=25, ge=5, le=100)
    connection_timeout: int = Field(default=30, ge=5, le=300)
    idle_timeout: int = Field(default=300, ge=60, le=3600)

    @model_validator(mode="after")
    def validate_pool_sizes(self) -> "DatabasePool":
        """Проверяет корректность размеров пула."""
        if self.min_connections > self.max_connections:
            raise ValueError("min_connections не может быть больше max_connections")
        return self


class DatabaseMigrations(BaseModel):
    """Настройки миграций БД."""

    auto_migrate: bool = Field(default=True)
    backup_before_migration: bool = Field(default=True)


class DatabaseSettings(BaseModel):
    """Настройки подключения к базе данных."""

    type: str = Field(default="postgresql")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5555, ge=1024, le=65535)
    name: str = Field(default="bot_trading_v3")
    user: str = Field(default="obertruper")
    password: Optional[str] = Field(default=None)  # Загружается из .env
    pool: DatabasePool = Field(default_factory=DatabasePool)
    migrations: DatabaseMigrations = Field(default_factory=DatabaseMigrations)

    @field_validator("port")
    @classmethod
    def validate_postgres_port(cls, v: int) -> int:
        """Проверяет, что используется правильный порт PostgreSQL."""
        if v != 5555:
            raise ValueError(
                f"КРИТИЧНО: PostgreSQL должен использовать порт 5555, а не {v}! "
                "Установите PGPORT=5555 в .env"
            )
        return v


# ============= Торговля =============


class OrderExecution(BaseModel):
    """Настройки исполнения ордеров."""

    default_leverage: int = Field(default=5, ge=1, le=20)
    min_order_size: float = Field(default=5.0, ge=1.0, le=1000.0)
    max_slippage: float = Field(default=0.002, ge=0.0001, le=0.01)
    use_limit_orders: bool = Field(default=False)
    default_order_type: OrderType = Field(default=OrderType.MARKET)

    @field_validator("default_leverage")
    @classmethod
    def validate_leverage(cls, v: int) -> int:
        """Проверяет, что leverage соответствует требованиям (5x для production)."""
        if v != 5:
            print(f"⚠️ ВНИМАНИЕ: Используется leverage {v}x вместо рекомендуемых 5x")
        return v


class SignalSettings(BaseModel):
    """Настройки обработки сигналов."""

    process_interval: int = Field(default=5, ge=1, le=60)
    max_signal_age: int = Field(default=300, ge=60, le=3600)
    min_confidence: float = Field(default=0.40, ge=0.0, le=1.0)
    min_strength: float = Field(default=0.40, ge=0.0, le=1.0)

    @field_validator("min_confidence", "min_strength")
    @classmethod
    def validate_thresholds(cls, v: float, info) -> float:
        """Валидирует пороговые значения для сигналов."""
        field_name = info.field_name
        if v < 0.35:
            print(
                f"⚠️ {field_name}={v} слишком низкое, "
                "может привести к большому количеству ложных сигналов"
            )
        elif v > 0.7:
            print(
                f"⚠️ {field_name}={v} слишком высокое, "
                "может привести к пропуску валидных сигналов"
            )
        return v


class MLThresholds(BaseModel):
    """Пороговые значения для ML сигналов."""

    buy_profit: float = Field(default=0.55, ge=0.0, le=1.0)
    buy_loss: float = Field(default=0.45, ge=0.0, le=1.0)
    sell_profit: float = Field(default=0.55, ge=0.0, le=1.0)
    sell_loss: float = Field(default=0.45, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_profit_loss_balance(self) -> "MLThresholds":
        """Проверяет баланс между profit и loss порогами."""
        if self.buy_profit + self.buy_loss > 1.5:
            print("⚠️ Сумма buy_profit и buy_loss слишком высока")
        if self.sell_profit + self.sell_loss > 1.5:
            print("⚠️ Сумма sell_profit и sell_loss слишком высока")
        return self


class SignalProcessing(BaseModel):
    """Обработка торговых сигналов."""

    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    min_volume: float = Field(default=100000, ge=0)
    ml_thresholds: MLThresholds = Field(default_factory=MLThresholds)


class TradingSettings(BaseModel):
    """Торговые настройки."""

    hedge_mode: bool = Field(default=True)
    category: str = Field(default="linear")
    orders: OrderExecution = Field(default_factory=OrderExecution)
    signals: SignalSettings = Field(default_factory=SignalSettings)
    signal_processing: SignalProcessing = Field(default_factory=SignalProcessing)
    max_positions_per_symbol: int = Field(default=1, ge=1, le=10)


# ============= Управление рисками =============


class GlobalRisk(BaseModel):
    """Глобальные параметры риска."""

    enabled: bool = Field(default=True)
    max_total_risk: float = Field(default=0.1, ge=0.01, le=1.0)
    max_daily_loss: float = Field(default=0.05, ge=0.01, le=0.5)
    max_open_positions: int = Field(default=10, ge=1, le=100)


class PositionRisk(BaseModel):
    """Параметры риска для позиций."""

    default_stop_loss: float = Field(default=0.02, ge=0.001, le=0.1)
    default_take_profit: float = Field(default=0.03, ge=0.001, le=0.5)
    max_position_size: float = Field(default=0.1, ge=0.01, le=1.0)
    position_size_percent: float = Field(default=2.0, ge=0.1, le=10.0)


class TrailingStop(BaseModel):
    """Настройки trailing stop."""

    enabled: bool = Field(default=True)
    activation_profit: float = Field(default=0.01, ge=0.001, le=0.1)
    trailing_distance: float = Field(default=0.005, ge=0.001, le=0.05)
    type: str = Field(default="percentage", pattern="^(percentage|absolute)$")
    step: float = Field(default=0.5, ge=0.1, le=5.0)
    min_profit: float = Field(default=0.3, ge=0.1, le=5.0)
    max_distance: float = Field(default=2.0, ge=0.5, le=10.0)


class PartialTakeProfitLevel(BaseModel):
    """Уровень частичного take profit."""

    percent: float = Field(ge=0.1, le=10.0)
    close_ratio: float = Field(ge=0.1, le=1.0)


class PartialTakeProfit(BaseModel):
    """Настройки частичного take profit."""

    enabled: bool = Field(default=True)
    update_sl_after_partial: bool = Field(default=True)
    levels: List[PartialTakeProfitLevel] = Field(default_factory=list)


class ProfitLockLevel(BaseModel):
    """Уровень блокировки профита."""

    trigger: float = Field(ge=0.1, le=20.0)
    lock: float = Field(ge=0.0, le=19.0)

    @model_validator(mode="after")
    def validate_lock_trigger(self) -> "ProfitLockLevel":
        """Проверяет, что lock меньше trigger."""
        if self.lock >= self.trigger:
            raise ValueError(f"lock ({self.lock}) должен быть меньше trigger ({self.trigger})")
        return self


class ProfitProtection(BaseModel):
    """Защита профита."""

    enabled: bool = Field(default=True)
    breakeven_percent: float = Field(default=1.0, ge=0.1, le=5.0)
    breakeven_offset: float = Field(default=0.2, ge=0.0, le=1.0)
    lock_percent: List[ProfitLockLevel] = Field(default_factory=list)
    max_updates: int = Field(default=5, ge=1, le=20)


class VolatilityAdjustment(BaseModel):
    """Корректировка по волатильности."""

    enabled: bool = Field(default=True)
    multiplier: float = Field(default=1.0, ge=0.5, le=3.0)


class EnhancedSLTP(BaseModel):
    """Улучшенные настройки SL/TP."""

    enabled: bool = Field(default=True)
    trailing_stop: TrailingStop = Field(default_factory=TrailingStop)
    partial_take_profit: PartialTakeProfit = Field(default_factory=PartialTakeProfit)
    profit_protection: ProfitProtection = Field(default_factory=ProfitProtection)
    volatility_adjustment: VolatilityAdjustment = Field(default_factory=VolatilityAdjustment)


class RiskManagementSettings(BaseModel):
    """Настройки управления рисками."""

    global_risk: GlobalRisk = Field(default_factory=GlobalRisk, alias="global")
    position: PositionRisk = Field(default_factory=PositionRisk)
    trailing_stop: TrailingStop = Field(default_factory=TrailingStop)
    enhanced_sltp: EnhancedSLTP = Field(default_factory=EnhancedSLTP)


# ============= ML настройки =============


class MLModel(BaseModel):
    """Настройки ML модели."""

    enabled: bool = Field(default=True)
    path: Path = Field(default=Path("models/saved/best_model.pth"))
    scaler_path: Path = Field(default=Path("models/saved/data_scaler.pkl"))
    device: str = Field(default="cuda", pattern="^(cuda|cpu|mps)$")

    @field_validator("path", "scaler_path")
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        """Проверяет существование файлов модели."""
        if not v.exists():
            print(f"⚠️ Файл {v} не найден")
        return v


class MLData(BaseModel):
    """Настройки данных для ML."""

    lookback_minutes: int = Field(default=3600, ge=60, le=10080)
    min_candles: int = Field(default=240, ge=50, le=1000)


class MLFilters(BaseModel):
    """Фильтры для ML предсказаний."""

    min_confidence: float = Field(default=0.40, ge=0.0, le=1.0)
    min_signal_strength: float = Field(default=0.40, ge=0.0, le=1.0)


class MLRisk(BaseModel):
    """Риск-параметры для ML."""

    max_positions_per_symbol: int = Field(default=1, ge=1, le=5)
    position_size_percent: float = Field(default=2.0, ge=0.1, le=10.0)


class MLSettings(BaseModel):
    """Настройки машинного обучения."""

    enabled: bool = Field(default=True)
    use_adapters: bool = Field(default=True)
    active_model: str = Field(default="patchtst")
    signal_generation_interval: int = Field(default=60, ge=10, le=3600)
    batch_size: int = Field(default=10, ge=1, le=100)
    parallel_workers: int = Field(default=4, ge=1, le=16)
    symbols: List[str] = Field(default_factory=list)
    model: MLModel = Field(default_factory=MLModel)
    data: MLData = Field(default_factory=MLData)
    filters: MLFilters = Field(default_factory=MLFilters)
    risk: MLRisk = Field(default_factory=MLRisk)
    models: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


# ============= Биржи =============


class RateLimits(BaseModel):
    """Лимиты запросов к бирже."""

    orders_per_second: int = Field(default=5, ge=1, le=50)
    requests_per_minute: int = Field(default=120, ge=10, le=1200)


class ExchangeConfig(BaseModel):
    """Конфигурация биржи."""

    enabled: bool = Field(default=False)
    api_key: Optional[str] = Field(default=None)
    api_secret: Optional[str] = Field(default=None)
    testnet: bool = Field(default=False)
    rate_limits: RateLimits = Field(default_factory=RateLimits)


class ExchangesSettings(BaseModel):
    """Настройки всех бирж."""

    bybit: ExchangeConfig = Field(default_factory=lambda: ExchangeConfig(enabled=True))
    binance: ExchangeConfig = Field(default_factory=ExchangeConfig)
    okx: ExchangeConfig = Field(default_factory=ExchangeConfig)
    gateio: ExchangeConfig = Field(default_factory=ExchangeConfig)
    kucoin: ExchangeConfig = Field(default_factory=ExchangeConfig)
    htx: ExchangeConfig = Field(default_factory=ExchangeConfig)
    bingx: ExchangeConfig = Field(default_factory=ExchangeConfig)


# ============= Мониторинг =============


class PrometheusConfig(BaseModel):
    """Настройки Prometheus."""

    enabled: bool = Field(default=True)
    port: int = Field(default=9090, ge=1024, le=65535)
    path: str = Field(default="/metrics")


class AlertThresholds(BaseModel):
    """Пороги для алертов."""

    memory_usage_percent: int = Field(default=85, ge=50, le=100)
    cpu_usage_percent: int = Field(default=90, ge=50, le=100)
    error_rate_percent: int = Field(default=5, ge=1, le=50)
    latency_ms: int = Field(default=1000, ge=100, le=10000)


class Alerts(BaseModel):
    """Настройки алертов."""

    enabled: bool = Field(default=True)
    telegram_enabled: bool = Field(default=False)
    email_enabled: bool = Field(default=False)
    thresholds: AlertThresholds = Field(default_factory=AlertThresholds)


class MonitoringSettings(BaseModel):
    """Настройки мониторинга."""

    enabled: bool = Field(default=True)
    health_check_interval: int = Field(default=30, ge=5, le=300)
    metrics_collection_interval: int = Field(default=10, ge=5, le=60)
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)
    alerts: Alerts = Field(default_factory=Alerts)


# ============= Логирование =============


class LogRotation(BaseModel):
    """Настройки ротации логов."""

    max_size_mb: int = Field(default=100, ge=10, le=1000)
    backup_count: int = Field(default=10, ge=1, le=100)


class LoggingSettings(BaseModel):
    """Настройки логирования."""

    level: LogLevel = Field(default=LogLevel.INFO)
    format: str = Field(default="structured", pattern="^(structured|plain|json)$")
    rotation: LogRotation = Field(default_factory=LogRotation)


# ============= Модели трейдеров =============


class IndicatorSettings(BaseModel):
    """Настройки индикатора."""
    type: str
    period: Optional[int] = None
    oversold: Optional[int] = None
    overbought: Optional[int] = None
    short_period: Optional[int] = None
    long_period: Optional[int] = None


class TraderCapitalSettings(BaseModel):
    """Настройки капитала трейдера."""
    initial: float = Field(default=10000, ge=0)
    per_trade_percentage: float = Field(default=2, ge=0.1, le=100)
    max_positions: int = Field(default=5, ge=1, le=50)


class TraderRiskSettings(BaseModel):
    """Настройки риска трейдера."""
    stop_loss_percentage: float = Field(default=2, ge=0.1, le=50)
    take_profit_percentage: float = Field(default=5, ge=0.1, le=100)
    max_drawdown_percentage: float = Field(default=10, ge=1, le=50)


class TraderStrategyConfig(BaseModel):
    """Конфигурация стратегии трейдера."""
    signal_interval: int = Field(default=60, ge=1)
    indicators: List[IndicatorSettings] = Field(default_factory=list)


class TraderSettings(BaseModel):
    """Настройки трейдера."""
    id: str
    enabled: bool = Field(default=True)
    type: str = Field(default="basic")
    symbols: List[str] = Field(default_factory=list)
    exchange: str
    strategy: str
    strategy_config: TraderStrategyConfig = Field(default_factory=TraderStrategyConfig)
    capital: TraderCapitalSettings = Field(default_factory=TraderCapitalSettings)
    risk_management: TraderRiskSettings = Field(default_factory=TraderRiskSettings)


# ============= Unified System Settings =============


class UnifiedSystemComponentSettings(BaseModel):
    """Настройки компонента unified системы."""

    enabled: bool = Field(default=True, description="Включен ли компонент")
    auto_restart: bool = Field(default=True, description="Автоматический перезапуск")
    health_check_interval: int = Field(default=30, description="Интервал проверки здоровья")
    startup_delay: int = Field(default=0, description="Задержка запуска в секундах")
    port: Optional[int] = Field(default=None, description="Порт компонента")
    integrated_with: Optional[str] = Field(default=None, description="Интегрирован с другим компонентом")
    health_check_endpoint: Optional[str] = Field(default=None, description="Эндпоинт для проверки здоровья")
    cwd: Optional[str] = Field(default=None, description="Рабочая директория")
    env: Dict[str, str] = Field(default_factory=dict, description="Переменные окружения")


class UnifiedSystemMonitoringSettings(BaseModel):
    """Настройки мониторинга unified системы."""

    interval_seconds: int = Field(default=30, description="Интервал мониторинга")
    auto_restart_on_failure: bool = Field(default=True, description="Автоперезапуск при сбое")
    max_restart_attempts: int = Field(default=5, description="Максимальное количество попыток перезапуска")
    restart_delay_seconds: int = Field(default=10, description="Задержка между перезапусками")


class UnifiedSystemLoggingSettings(BaseModel):
    """Настройки логирования unified системы."""

    aggregate_logs: bool = Field(default=True, description="Агрегировать логи")
    log_directory: str = Field(default="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/data/logs", description="Директория логов")
    process_log_directory: str = Field(default="/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/data/logs/processes", description="Директория логов процессов")


class UnifiedSystemSettings(BaseModel):
    """Настройки unified системы запуска."""

    enabled: bool = Field(default=True, description="Включена ли unified система")
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Настройки компонентов")
    monitoring: UnifiedSystemMonitoringSettings = Field(default_factory=UnifiedSystemMonitoringSettings)
    logging: UnifiedSystemLoggingSettings = Field(default_factory=UnifiedSystemLoggingSettings)


# ============= Корневая модель конфигурации =============


class RootConfig(BaseModel):
    """Корневая модель конфигурации системы.

    Объединяет все подсистемы в единую валидируемую структуру.
    """

    system: SystemSettings = Field(default_factory=SystemSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)
    risk_management: RiskManagementSettings = Field(default_factory=RiskManagementSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    exchanges: ExchangesSettings = Field(default_factory=ExchangesSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    unified_system: UnifiedSystemSettings = Field(default_factory=UnifiedSystemSettings)
    traders: List[TraderSettings] = Field(default_factory=list)

    class Config:
        """Настройки Pydantic модели."""

        use_enum_values = True
        validate_assignment = True
        extra = "allow"  # Разрешаем дополнительные поля для обратной совместимости
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
        }

    def validate_consistency(self) -> List[str]:
        """Проверяет консистентность конфигурации между разделами.

        Returns:
            Список предупреждений о несоответствиях.
        """
        warnings = []

        # Проверка соответствия leverage в разных местах
        if self.trading.orders.default_leverage != 5:
            warnings.append(
                f"Leverage {self.trading.orders.default_leverage}x "
                "отличается от рекомендуемых 5x для production"
            )

        # Проверка ML настроек
        if self.ml.enabled and not self.ml.model.path.exists():
            warnings.append(f"ML включен, но модель не найдена: {self.ml.model.path}")

        # Проверка, что хотя бы одна биржа включена
        exchanges_dict = self.exchanges.model_dump()
        if not any(ex.get("enabled") for ex in exchanges_dict.values()):
            warnings.append("Ни одна биржа не активирована")

        # Проверка соответствия риск-параметров
        if self.risk_management.position.position_size_percent > 5:
            warnings.append(
                f"position_size_percent={self.risk_management.position.position_size_percent}% "
                "слишком высок для безопасной торговли"
            )

        return warnings

    def get_frontend_safe_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию, безопасную для передачи в frontend.

        Исключает все секретные данные и чувствительную информацию.
        """
        config_dict = self.model_dump()

        # Удаляем секретные данные
        for exchange in config_dict.get("exchanges", {}).values():
            exchange.pop("api_key", None)
            exchange.pop("api_secret", None)

        # Удаляем пароль БД
        if "database" in config_dict:
            config_dict["database"].pop("password", None)

        return config_dict