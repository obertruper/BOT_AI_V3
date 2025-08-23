"""Модуль кастомных исключений для системы BOT_Trading v3.0.

Определяет иерархию классов исключений для стандартизированной обработки
ошибок во всех компонентах системы. Каждое исключение содержит
контекстную информацию, такую как категория, уровень серьезности и компонент,
в котором произошла ошибка.
"""

from datetime import datetime
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Перечисление уровней серьезности ошибок."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Перечисление категорий ошибок для их классификации."""

    CONFIGURATION = "configuration"
    TRADER = "trader"
    EXCHANGE = "exchange"
    STRATEGY = "strategy"
    ML = "ml"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    RISK_MANAGEMENT = "risk_management"


class BaseTradingError(Exception):
    """Базовый класс для всех кастомных исключений в приложении.

    Args:
        message: Сообщение об ошибке.
        severity: Уровень серьезности (из ErrorSeverity).
        category: Категория ошибки (из ErrorCategory).
        context: Словарь с дополнительным контекстом.
        original_exception: Исходное исключение, если есть.
        component: Название компонента, где произошла ошибка.
        trader_id: ID трейдера, если применимо.
        error_code: Уникальный код ошибки.
    """

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
        component: str | None = None,
        trader_id: str | None = None,
        error_code: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.original_exception = original_exception
        self.component = component
        self.trader_id = trader_id
        self.error_code = error_code
        self.timestamp = datetime.now()

        if original_exception:
            self.context["original_error"] = {
                "type": type(original_exception).__name__,
                "message": str(original_exception),
                "args": original_exception.args,
            }

    def to_dict(self) -> dict[str, Any]:
        """Преобразует исключение в словарь для удобного логирования."""
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "component": self.component,
            "trader_id": self.trader_id,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }

class ConfigurationError(BaseTradingError):
    """Исключение для ошибок конфигурации системы."""
    
    def __init__(
        self,
        message: str,
        config_key: str = None,
        config_file: str = None,
        **kwargs
    ):
        """Инициализирует исключение конфигурации.
        
        Args:
            message: Описание ошибки
            config_key: Ключ конфигурации с ошибкой
            config_file: Файл конфигурации с ошибкой
        """
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        if config_file:
            context["config_file"] = config_file
            
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            error_code="CONFIG_ERROR",
            **kwargs
        )


class DataLoadError(BaseTradingError):
    """Ошибка загрузки данных."""
    pass


class ComponentInitializationError(BaseTradingError):
    """Ошибка инициализации компонента системы."""
    pass


class UnsupportedExchangeError(BaseTradingError):
    """Исключение для неподдерживаемой биржи."""

    def __init__(
        self,
        message: str,
        exchange_name: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.EXCHANGE,
            severity=severity,
            component="Exchange",
            context={"exchange_name": exchange_name} if exchange_name else {},
            **kwargs,
        )


class UnsupportedStrategyError(BaseTradingError):
    """Исключение для неподдерживаемой стратегии."""

    def __init__(
        self,
        message: str,
        strategy_name: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.STRATEGY,
            severity=severity,
            component="Strategy",
            context={"strategy_name": strategy_name} if strategy_name else {},
            **kwargs,
        )


class ExchangeError(BaseTradingError):
    """Ошибка загрузки данных."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            error_code="DATA_LOAD_ERROR",
            **kwargs
        )


class TraderFactoryError(BaseTradingError):
    """Исключение для ошибок в фабрике трейдеров."""

    def __init__(
        self,
        message: str,
        trader_type: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.TRADER,
            severity=severity,
            component="TraderFactory",
            context={"trader_type": trader_type} if trader_type else {},
            **kwargs,
        )


class TraderInitializationError(BaseTradingError):
    """Исключение для ошибок инициализации трейдера."""

    def __init__(
        self,
        message: str,
        trader_id: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.TRADER,
            severity=severity,
            component="TraderInitialization",
            trader_id=trader_id,
            **kwargs,
        )


class TraderConfigurationError(BaseTradingError):
    """Исключение для ошибок конфигурации трейдера."""

    def __init__(
        self,
        message: str,
        trader_id: str = None,
        config_key: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.TRADER,
            severity=severity,
            component="TraderConfiguration",
            trader_id=trader_id,
            context={"config_key": config_key} if config_key else {},
            **kwargs,
        )


class TraderError(BaseTradingError):
    """Ошибка работы трейдера."""
    
    def __init__(self, message: str, trader_id: str = None, **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.TRADER,
            trader_id=trader_id,
            error_code="TRADER_ERROR",
            **kwargs
        )


class TooManyTradersError(TraderError):
    """Исключение для превышения лимита количества трейдеров."""
    
    def __init__(self, message: str, max_traders: int = None, current_count: int = None, **kwargs):
        super().__init__(
            message=message,
            error_code="TOO_MANY_TRADERS",
            **kwargs
        )
        self.max_traders = max_traders
        self.current_count = current_count


class TraderAlreadyExistsError(TraderError):
    """Исключение для дублирования трейдера."""
    
    def __init__(self, message: str, trader_id: str = None, **kwargs):
        super().__init__(
            message=message,
            trader_id=trader_id,
            error_code="TRADER_ALREADY_EXISTS",
            **kwargs
        )


class TraderNotFoundError(TraderError):
    """Исключение для отсутствующего трейдера."""
    
    def __init__(self, message: str, trader_id: str = None, **kwargs):
        super().__init__(
            message=message,
            trader_id=trader_id,
            error_code="TRADER_NOT_FOUND",
            **kwargs
        )


class TraderManagerError(TraderError):
    """Исключение для ошибок менеджера трейдеров."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="TRADER_MANAGER_ERROR",
            **kwargs
        )


class StrategyError(BaseTradingError):
    """Ошибка торговой стратегии."""
    
    def __init__(self, message: str, strategy_name: str = None, **kwargs):
        context = kwargs.get("context", {})
        if strategy_name:
            context["strategy_name"] = strategy_name
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.STRATEGY,
            context=context,
            error_code="STRATEGY_ERROR",
            **kwargs
        )


class MLModelError(BaseTradingError):
    """Ошибка ML модели."""
    
    def __init__(self, message: str, model_name: str = None, **kwargs):
        context = kwargs.get("context", {})
        if model_name:
            context["model_name"] = model_name
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.ML,
            context=context,
            error_code="ML_MODEL_ERROR",
            **kwargs
        )


class NetworkError(BaseTradingError):
    """Ошибка сети."""
    
    def __init__(self, message: str, url: str = None, **kwargs):
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            error_code="NETWORK_ERROR",
            **kwargs
        )


class ValidationError(BaseTradingError):
    """Ошибка валидации данных."""
    
    def __init__(self, message: str, field_name: str = None, **kwargs):
        context = kwargs.get("context", {})
        if field_name:
            context["field_name"] = field_name
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            context=context,
            error_code="VALIDATION_ERROR",
            **kwargs
        )


class AuthenticationError(BaseTradingError):
    """Ошибка аутентификации."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHENTICATION,
            error_code="AUTH_ERROR",
            **kwargs
        )


class SystemError(BaseTradingError):
    """Исключение для системных ошибок."""

    def __init__(
        self,
        message: str,
        component: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=severity,
            component=component or "System",
            **kwargs,
        )


class SystemInitializationError(BaseTradingError):
    """Исключение для ошибок инициализации системы."""

    def __init__(
        self,
        message: str,
        component: str = None,
        severity: ErrorSeverity = ErrorSeverity.CRITICAL,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=severity,
            component=component or "SystemInitialization",
            **kwargs,
        )


class SystemShutdownError(BaseTradingError):
    """Исключение для ошибок завершения работы системы."""

    def __init__(
        self,
        message: str,
        component: str = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=severity,
            component=component or "SystemShutdown",
            **kwargs,
        )


class HealthCheckError(BaseTradingError):
    """Исключение для ошибок проверки здоровья системы."""

    def __init__(
        self,
        message: str,
        component: str = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        **kwargs,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=severity,
            component=component or "HealthCheck",
            **kwargs,
        )


class RiskManagementError(BaseTradingError):
    """Ошибка управления рисками."""
    
    def __init__(self, message: str, risk_type: str = None, **kwargs):
        context = kwargs.get("context", {})
        if risk_type:
            context["risk_type"] = risk_type
        
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.RISK_MANAGEMENT,
            context=context,
            error_code="RISK_ERROR",
            **kwargs
        )


class LeverageError(BaseTradingError):
    """Ошибка работы с плечом."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.RISK_MANAGEMENT,
            error_code="LEVERAGE_ERROR",
            **kwargs
        )
