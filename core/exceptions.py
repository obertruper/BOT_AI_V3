"""
Comprehensive Exception System для BOT_Trading v3.0

Расширенная система исключений с поддержкой:
- Мульти-трейдер ошибок с контекстом
- Специфических исключений для каждой биржи
- ML и стратегических ошибок
- Системных и конфигурационных ошибок
- Подробного контекста для debugging
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Уровни серьезности ошибок"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Категории ошибок"""

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
    """
    Базовый класс для всех ошибок торговой системы

    Предоставляет единый интерфейс для всех исключений с:
    - Контекстной информацией
    - Уровнем серьезности
    - Категорией ошибки
    - Временными метками
    - Дополнительными данными для debugging
    """

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
        component: Optional[str] = None,
        trader_id: Optional[str] = None,
        error_code: Optional[str] = None,
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

        # Автоматически добавляем информацию об оригинальном исключении
        if original_exception:
            self.context["original_error"] = {
                "type": type(original_exception).__name__,
                "message": str(original_exception),
                "args": original_exception.args,
            }

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование исключения в словарь для логирования"""
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

    def __str__(self) -> str:
        parts = [f"{type(self).__name__}: {self.message}"]

        if self.trader_id:
            parts.append(f"[Trader: {self.trader_id}]")

        if self.component:
            parts.append(f"[Component: {self.component}]")

        if self.error_code:
            parts.append(f"[Code: {self.error_code}]")

        return " ".join(parts)


# =================== CONFIGURATION ERRORS ===================


class ConfigurationError(BaseTradingError):
    """Базовая ошибка конфигурации"""

    def __init__(self, message: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            **kwargs,
        )
        if config_path:
            self.context["config_path"] = config_path


class ConfigValidationError(ConfigurationError):
    """Ошибка валидации конфигурации"""

    def __init__(self, field: str, expected: str, actual: Any, **kwargs):
        message = (
            f"Validation failed for field '{field}': expected {expected}, got {actual}"
        )
        super().__init__(message, **kwargs)
        self.context.update({"field": field, "expected": expected, "actual": actual})


class LoggingConfigurationError(ConfigurationError):
    """Ошибка конфигурации логирования"""

    pass


# =================== TRADER ERRORS ===================


class TraderError(BaseTradingError):
    """Базовая ошибка трейдера"""

    def __init__(self, message: str, trader_id: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TRADER,
            trader_id=trader_id,
            **kwargs,
        )


class TraderInitializationError(TraderError):
    """Ошибка инициализации трейдера"""

    def __init__(
        self,
        message: str,
        trader_id: str,
        failed_component: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, trader_id, severity=ErrorSeverity.HIGH, **kwargs)
        if failed_component:
            self.context["failed_component"] = failed_component


class TraderConfigurationError(TraderError):
    """Ошибка конфигурации трейдера"""

    def __init__(
        self, message: str, trader_id: str, config_field: Optional[str] = None, **kwargs
    ):
        super().__init__(message, trader_id, **kwargs)
        if config_field:
            self.context["config_field"] = config_field


class TraderFactoryError(BaseTradingError):
    """Ошибка фабрики трейдеров"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.TRADER,
            component="trader_factory",
            **kwargs,
        )


class TraderManagerError(BaseTradingError):
    """Ошибка менеджера трейдеров"""

    def __init__(
        self, message: str, affected_traders: Optional[List[str]] = None, **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.TRADER,
            component="trader_manager",
            **kwargs,
        )
        if affected_traders:
            self.context["affected_traders"] = affected_traders


class TraderNotFoundError(TraderError):
    """Трейдер не найден"""

    def __init__(self, trader_id: str, **kwargs):
        super().__init__(f"Trader '{trader_id}' not found", trader_id, **kwargs)


class TraderAlreadyExistsError(TraderError):
    """Трейдер уже существует"""

    def __init__(self, trader_id: str, **kwargs):
        super().__init__(f"Trader '{trader_id}' already exists", trader_id, **kwargs)


class TooManyTradersError(BaseTradingError):
    """Превышен лимит трейдеров"""

    def __init__(self, current_count: int, max_limit: int, **kwargs):
        message = f"Too many traders: {current_count}/{max_limit}"
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TRADER,
            **kwargs,
        )
        self.context.update({"current_count": current_count, "max_limit": max_limit})


# =================== EXCHANGE ERRORS ===================


class ExchangeError(BaseTradingError):
    """Базовая ошибка биржи"""

    def __init__(self, message: str, exchange_name: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXCHANGE,
            component=f"exchange_{exchange_name}",
            **kwargs,
        )
        self.exchange_name = exchange_name
        self.context["exchange_name"] = exchange_name


class UnsupportedExchangeError(ExchangeError):
    """Неподдерживаемая биржа"""

    def __init__(
        self,
        exchange_name: str,
        supported_exchanges: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Unsupported exchange: {exchange_name}"
        if supported_exchanges:
            message += f". Supported: {', '.join(supported_exchanges)}"

        super().__init__(message, exchange_name, **kwargs)
        if supported_exchanges:
            self.context["supported_exchanges"] = supported_exchanges


class ExchangeConnectionError(ExchangeError):
    """Ошибка подключения к бирже"""

    def __init__(self, exchange_name: str, endpoint: Optional[str] = None, **kwargs):
        message = f"Connection failed to {exchange_name}"
        if endpoint:
            message += f" endpoint: {endpoint}"

        super().__init__(message, exchange_name, severity=ErrorSeverity.HIGH, **kwargs)
        if endpoint:
            self.context["endpoint"] = endpoint


class ExchangeAuthenticationError(ExchangeError):
    """Ошибка аутентификации на бирже"""

    def __init__(self, exchange_name: str, **kwargs):
        super().__init__(
            f"Authentication failed for {exchange_name}",
            exchange_name,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AUTHENTICATION,
            **kwargs,
        )


class ExchangeAPIError(ExchangeError):
    """Ошибка API биржи"""

    def __init__(
        self,
        exchange_name: str,
        api_method: str,
        status_code: Optional[int] = None,
        api_message: Optional[str] = None,
        **kwargs,
    ):
        message = f"API error in {exchange_name}.{api_method}"
        if status_code:
            message += f" (HTTP {status_code})"
        if api_message:
            message += f": {api_message}"

        super().__init__(message, exchange_name, **kwargs)
        self.context.update(
            {
                "api_method": api_method,
                "status_code": status_code,
                "api_message": api_message,
            }
        )


class ExchangeRateLimitError(ExchangeError):
    """Превышен rate limit биржи"""

    def __init__(self, exchange_name: str, retry_after: Optional[int] = None, **kwargs):
        message = f"Rate limit exceeded for {exchange_name}"
        if retry_after:
            message += f", retry after {retry_after} seconds"

        super().__init__(message, exchange_name, **kwargs)
        if retry_after:
            self.context["retry_after"] = retry_after


class InsufficientBalanceError(ExchangeError):
    """Недостаточный баланс"""

    def __init__(
        self,
        exchange_name: str,
        required_amount: float,
        available_balance: float,
        currency: str,
        **kwargs,
    ):
        message = f"Insufficient balance on {exchange_name}: need {required_amount} {currency}, have {available_balance} {currency}"
        super().__init__(message, exchange_name, **kwargs)
        self.context.update(
            {
                "required_amount": required_amount,
                "available_balance": available_balance,
                "currency": currency,
            }
        )


# =================== STRATEGY ERRORS ===================


class StrategyError(BaseTradingError):
    """Базовая ошибка стратегии"""

    def __init__(
        self,
        message: str,
        strategy_name: str,
        trader_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.STRATEGY,
            component=f"strategy_{strategy_name}",
            trader_id=trader_id,
            **kwargs,
        )
        self.strategy_name = strategy_name
        self.context["strategy_name"] = strategy_name


class UnsupportedStrategyError(StrategyError):
    """Неподдерживаемая стратегия"""

    def __init__(
        self,
        strategy_name: str,
        supported_strategies: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Unsupported strategy: {strategy_name}"
        if supported_strategies:
            message += f". Supported: {', '.join(supported_strategies)}"

        super().__init__(message, strategy_name, **kwargs)
        if supported_strategies:
            self.context["supported_strategies"] = supported_strategies


class StrategyInitializationError(StrategyError):
    """Ошибка инициализации стратегии"""

    def __init__(self, strategy_name: str, reason: str, **kwargs):
        super().__init__(
            f"Failed to initialize strategy {strategy_name}: {reason}",
            strategy_name,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class SignalGenerationError(StrategyError):
    """Ошибка генерации сигнала"""

    def __init__(self, strategy_name: str, symbol: str, reason: str, **kwargs):
        super().__init__(
            f"Signal generation failed for {symbol} in {strategy_name}: {reason}",
            strategy_name,
            **kwargs,
        )
        self.context.update({"symbol": symbol, "reason": reason})


# =================== ML ERRORS ===================


class MLError(BaseTradingError):
    """Базовая ошибка ML системы"""

    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.ML,
            component="ml_system",
            **kwargs,
        )
        if model_name:
            self.context["model_name"] = model_name


class ModelLoadError(MLError):
    """Ошибка загрузки ML модели"""

    def __init__(self, model_name: str, model_path: str, **kwargs):
        super().__init__(
            f"Failed to load model '{model_name}' from {model_path}",
            model_name,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )
        self.context["model_path"] = model_path


class PredictionError(MLError):
    """Ошибка предсказания ML модели"""

    def __init__(self, model_name: str, features_count: Optional[int] = None, **kwargs):
        message = f"Prediction failed for model '{model_name}'"
        if features_count is not None:
            message += f" with {features_count} features"

        super().__init__(message, model_name, **kwargs)
        if features_count is not None:
            self.context["features_count"] = features_count


class FeatureExtractionError(MLError):
    """Ошибка извлечения признаков"""

    def __init__(self, feature_name: str, data_source: str, **kwargs):
        super().__init__(
            f"Feature extraction failed for '{feature_name}' from {data_source}",
            **kwargs,
        )
        self.context.update({"feature_name": feature_name, "data_source": data_source})


# =================== DATABASE ERRORS ===================


class DatabaseError(BaseTradingError):
    """Базовая ошибка базы данных"""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            component="database",
            **kwargs,
        )
        if operation:
            self.context["operation"] = operation


class DatabaseConnectionError(DatabaseError):
    """Ошибка подключения к базе данных"""

    def __init__(self, database_url: str, **kwargs):
        super().__init__(
            f"Failed to connect to database: {database_url}",
            severity=ErrorSeverity.CRITICAL,
            **kwargs,
        )
        self.context["database_url"] = database_url


class RepositoryError(DatabaseError):
    """Ошибка репозитория"""

    def __init__(self, repository_name: str, operation: str, **kwargs):
        super().__init__(
            f"Repository operation failed: {repository_name}.{operation}",
            operation=operation,
            **kwargs,
        )
        self.context["repository_name"] = repository_name


# =================== NETWORK ERRORS ===================


class NetworkError(BaseTradingError):
    """Базовая сетевая ошибка"""

    def __init__(self, message: str, endpoint: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            **kwargs,
        )
        if endpoint:
            self.context["endpoint"] = endpoint


class ConnectionTimeoutError(NetworkError):
    """Таймаут соединения"""

    def __init__(self, endpoint: str, timeout_seconds: float, **kwargs):
        super().__init__(
            f"Connection timeout to {endpoint} after {timeout_seconds}s",
            endpoint=endpoint,
            **kwargs,
        )
        self.context["timeout_seconds"] = timeout_seconds


class WebSocketError(NetworkError):
    """Ошибка WebSocket соединения"""

    def __init__(self, message: str, ws_url: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if ws_url:
            self.context["ws_url"] = ws_url


# =================== RISK MANAGEMENT ERRORS ===================


class RiskManagementError(BaseTradingError):
    """Базовая ошибка управления рисками"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.RISK_MANAGEMENT,
            component="risk_manager",
            **kwargs,
        )


class RiskLimitExceededError(RiskManagementError):
    """Превышен риск-лимит"""

    def __init__(
        self,
        limit_type: str,
        current_value: float,
        max_allowed: float,
        trader_id: Optional[str] = None,
        **kwargs,
    ):
        message = (
            f"Risk limit exceeded: {limit_type} = {current_value}, max = {max_allowed}"
        )
        super().__init__(message, trader_id=trader_id, **kwargs)
        self.context.update(
            {
                "limit_type": limit_type,
                "current_value": current_value,
                "max_allowed": max_allowed,
            }
        )


class InvalidPositionSizeError(RiskManagementError):
    """Некорректный размер позиции"""

    def __init__(
        self, position_size: float, min_size: float, max_size: float, **kwargs
    ):
        message = (
            f"Invalid position size: {position_size} (allowed: {min_size} - {max_size})"
        )
        super().__init__(message, **kwargs)
        self.context.update(
            {"position_size": position_size, "min_size": min_size, "max_size": max_size}
        )


# =================== VALIDATION ERRORS ===================


class ValidationError(BaseTradingError):
    """Базовая ошибка валидации"""

    def __init__(
        self, message: str, field: Optional[str] = None, value: Any = None, **kwargs
    ):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            **kwargs,
        )
        if field:
            self.context["field"] = field
        if value is not None:
            self.context["value"] = value


class OrderValidationError(ValidationError):
    """Ошибка валидации ордера"""

    def __init__(
        self, reason: str, order_data: Optional[Dict[str, Any]] = None, **kwargs
    ):
        super().__init__(f"Order validation failed: {reason}", **kwargs)
        if order_data:
            self.context["order_data"] = order_data


# =================== SYSTEM ERRORS ===================


class SystemError(BaseTradingError):
    """Базовая системная ошибка"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.SYSTEM,
            **kwargs,
        )


class OrchestratorError(SystemError):
    """Ошибка системного оркестратора"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, component="orchestrator", **kwargs)


class ComponentInitializationError(SystemError):
    """Ошибка инициализации компонента"""

    def __init__(self, component_name: str, reason: str, **kwargs):
        super().__init__(
            f"Failed to initialize component '{component_name}': {reason}",
            component=component_name,
            severity=ErrorSeverity.CRITICAL,
            **kwargs,
        )


class ResourceExhaustedError(SystemError):
    """Исчерпание системных ресурсов"""

    def __init__(
        self, resource_type: str, current_usage: float, limit: float, **kwargs
    ):
        message = f"Resource exhausted: {resource_type} usage {current_usage:.1f}% (limit: {limit:.1f}%)"
        super().__init__(message, severity=ErrorSeverity.CRITICAL, **kwargs)
        self.context.update(
            {
                "resource_type": resource_type,
                "current_usage": current_usage,
                "limit": limit,
            }
        )


# =================== UTILITY FUNCTIONS ===================


def create_error_context(**kwargs) -> Dict[str, Any]:
    """Создание контекста ошибки с дополнительной информацией"""
    context = {}

    # Добавляем только не-None значения
    for key, value in kwargs.items():
        if value is not None:
            context[key] = value

    return context


def log_exception(logger, exception: BaseTradingError) -> None:
    """Логирование исключения с полным контекстом"""
    logger.error(
        f"{exception.message}",
        extra={
            "error_dict": exception.to_dict(),
            "trader_id": exception.trader_id,
            "component": exception.component,
            "severity": exception.severity.value,
            "category": exception.category.value,
        },
    )


def handle_and_log_error(
    logger, error: Exception, context: Optional[Dict[str, Any]] = None
) -> BaseTradingError:
    """
    Обработка и логирование произвольной ошибки

    Преобразует обычное исключение в BaseTradingError и логирует его
    """
    if isinstance(error, BaseTradingError):
        trading_error = error
    else:
        trading_error = BaseTradingError(
            message=str(error), original_exception=error, context=context
        )

    log_exception(logger, trading_error)
    return trading_error
