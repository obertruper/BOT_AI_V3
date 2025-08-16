"""
Исключения для мульти-биржевой системы BOT_Trading v3.0

Содержит специфические исключения для работы с различными биржами:
- Ошибки подключения и аутентификации
- API ошибки и превышения лимитов
- Торговые ошибки и валидация
- WebSocket ошибки
"""

from datetime import datetime
from typing import Any

# Импортируем базовые исключения из core
from core.exceptions import (
    ErrorCategory,
    ErrorSeverity,
)
from core.exceptions import ExchangeError as CoreExchangeError
from core.exceptions import NetworkError as CoreNetworkError


class ExchangeError(CoreExchangeError):
    """Базовая ошибка биржи с расширенной функциональностью"""

    def __init__(
        self,
        message: str,
        exchange_name: str,
        endpoint: str | None = None,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(message, exchange_name, **kwargs)

        # Дополнительная информация для биржевых ошибок
        if endpoint:
            self.context["endpoint"] = endpoint
        if status_code:
            self.context["status_code"] = status_code
        if response_data:
            self.context["response_data"] = response_data


class ConnectionError(ExchangeError):
    """Ошибка подключения к бирже"""

    def __init__(
        self,
        exchange_name: str,
        endpoint: str | None = None,
        timeout: float | None = None,
        **kwargs,
    ):
        message = f"Failed to connect to {exchange_name}"
        if endpoint:
            message += f" endpoint: {endpoint}"
        if timeout:
            message += f" (timeout: {timeout}s)"

        super().__init__(
            message,
            exchange_name,
            endpoint=endpoint,
            **kwargs,
        )
        # Устанавливаем severity после инициализации базового класса
        self.severity = ErrorSeverity.HIGH

        if timeout:
            self.context["timeout"] = timeout


class AuthenticationError(ExchangeError):
    """Ошибка аутентификации на бирже"""

    def __init__(self, exchange_name: str, auth_type: str = "API_KEY", **kwargs):
        message = f"Authentication failed for {exchange_name} using {auth_type}"

        super().__init__(
            message,
            exchange_name,
            **kwargs,
        )
        # Устанавливаем severity и category после инициализации базового класса
        self.severity = ErrorSeverity.CRITICAL
        self.category = ErrorCategory.AUTHENTICATION

        self.context["auth_type"] = auth_type


class APIError(ExchangeError):
    """Ошибка API биржи"""

    def __init__(
        self,
        exchange_name: str,
        api_method: str,
        error_code: str | None = None,
        api_message: str | None = None,
        status_code: int | None = None,
        **kwargs,
    ):
        message = f"API error in {exchange_name}.{api_method}"
        if error_code:
            message += f" (Code: {error_code})"
        if api_message:
            message += f": {api_message}"

        super().__init__(message, exchange_name, status_code=status_code, **kwargs)

        self.context.update(
            {
                "api_method": api_method,
                "api_error_code": error_code,
                "api_message": api_message,
            }
        )


class RateLimitError(ExchangeError):
    """Превышение rate limit биржи"""

    def __init__(
        self,
        exchange_name: str,
        limit_type: str = "requests",
        retry_after: int | None = None,
        current_usage: int | None = None,
        limit_value: int | None = None,
        **kwargs,
    ):
        message = f"Rate limit exceeded for {exchange_name} ({limit_type})"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        if current_usage and limit_value:
            message += f" (usage: {current_usage}/{limit_value})"

        super().__init__(message, exchange_name, severity=ErrorSeverity.MEDIUM, **kwargs)

        self.context.update(
            {
                "limit_type": limit_type,
                "retry_after": retry_after,
                "current_usage": current_usage,
                "limit_value": limit_value,
            }
        )


class InsufficientBalanceError(ExchangeError):
    """Недостаточный баланс на бирже"""

    def __init__(
        self,
        exchange_name: str,
        required_amount: float,
        available_balance: float,
        currency: str,
        account_type: str = "trading",
        **kwargs,
    ):
        message = (
            f"Insufficient balance on {exchange_name}: "
            f"need {required_amount} {currency}, "
            f"have {available_balance} {currency} "
            f"in {account_type} account"
        )

        super().__init__(message, exchange_name, severity=ErrorSeverity.HIGH, **kwargs)

        self.context.update(
            {
                "required_amount": required_amount,
                "available_balance": available_balance,
                "currency": currency,
                "account_type": account_type,
                "shortfall": required_amount - available_balance,
            }
        )


class OrderError(ExchangeError):
    """Ошибки при работе с ордерами"""

    def __init__(
        self,
        exchange_name: str,
        operation: str,
        order_id: str | None = None,
        symbol: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        message = f"Order {operation} failed on {exchange_name}"
        if order_id:
            message += f" for order {order_id}"
        if symbol:
            message += f" ({symbol})"
        if reason:
            message += f": {reason}"

        super().__init__(message, exchange_name, **kwargs)

        self.context.update(
            {
                "operation": operation,
                "order_id": order_id,
                "symbol": symbol,
                "reason": reason,
            }
        )


class OrderNotFoundError(OrderError):
    """Ордер не найден"""

    def __init__(self, exchange_name: str, order_id: str, symbol: str | None = None, **kwargs):
        super().__init__(
            exchange_name,
            "lookup",
            order_id=order_id,
            symbol=symbol,
            reason="Order not found",
            **kwargs,
        )


class OrderRejectedError(OrderError):
    """Ордер отклонен биржей"""

    def __init__(
        self,
        exchange_name: str,
        symbol: str,
        rejection_reason: str,
        order_data: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(
            exchange_name, "placement", symbol=symbol, reason=rejection_reason, **kwargs
        )

        if order_data:
            self.context["order_data"] = order_data


class PositionError(ExchangeError):
    """Ошибки при работе с позициями"""

    def __init__(
        self,
        exchange_name: str,
        operation: str,
        symbol: str,
        reason: str | None = None,
        **kwargs,
    ):
        message = f"Position {operation} failed on {exchange_name} for {symbol}"
        if reason:
            message += f": {reason}"

        super().__init__(message, exchange_name, **kwargs)

        self.context.update({"operation": operation, "symbol": symbol, "reason": reason})


class PositionNotFoundError(PositionError):
    """Позиция не найдена"""

    def __init__(self, exchange_name: str, symbol: str, **kwargs):
        super().__init__(exchange_name, "lookup", symbol, reason="Position not found", **kwargs)


class LeverageError(ExchangeError):
    """Ошибки при работе с плечом"""

    def __init__(
        self,
        exchange_name: str,
        symbol: str,
        requested_leverage: float,
        max_leverage: float | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        message = (
            f"Leverage operation failed on {exchange_name} for {symbol}: {requested_leverage}x"
        )
        if max_leverage:
            message += f" (max allowed: {max_leverage}x)"
        if reason:
            message += f" - {reason}"

        super().__init__(message, exchange_name, **kwargs)

        self.context.update(
            {
                "symbol": symbol,
                "requested_leverage": requested_leverage,
                "max_leverage": max_leverage,
                "reason": reason,
            }
        )


class MarketDataError(ExchangeError):
    """Ошибки при получении рыночных данных"""

    def __init__(
        self,
        exchange_name: str,
        data_type: str,
        symbol: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        message = f"Failed to get {data_type} from {exchange_name}"
        if symbol:
            message += f" for {symbol}"
        if reason:
            message += f": {reason}"

        super().__init__(message, exchange_name, **kwargs)

        self.context.update({"data_type": data_type, "symbol": symbol, "reason": reason})


class WebSocketError(CoreNetworkError):
    """Ошибки WebSocket соединения"""

    def __init__(
        self,
        exchange_name: str,
        operation: str,
        ws_url: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        message = f"WebSocket {operation} failed for {exchange_name}"
        if reason:
            message += f": {reason}"

        super().__init__(message, **kwargs)

        self.context.update(
            {
                "exchange_name": exchange_name,
                "operation": operation,
                "ws_url": ws_url,
                "reason": reason,
            }
        )


class SubscriptionError(WebSocketError):
    """Ошибка подписки WebSocket"""

    def __init__(
        self,
        exchange_name: str,
        channel: str,
        symbol: str | None = None,
        reason: str | None = None,
        **kwargs,
    ):
        message = f"Failed to subscribe to {channel}"
        if symbol:
            message += f" for {symbol}"

        super().__init__(
            exchange_name,
            "subscription",
            reason=message + (f": {reason}" if reason else ""),
            **kwargs,
        )

        self.context.update({"channel": channel, "symbol": symbol})


class ValidationError(ExchangeError):
    """Ошибки валидации данных"""

    def __init__(
        self,
        exchange_name: str,
        validation_type: str,
        field: str,
        value: Any,
        expected: str,
        **kwargs,
    ):
        message = f"Validation failed for {validation_type} on {exchange_name}: {field}={value}, expected {expected}"

        super().__init__(message, exchange_name, category=ErrorCategory.VALIDATION, **kwargs)

        self.context.update(
            {
                "validation_type": validation_type,
                "field": field,
                "value": value,
                "expected": expected,
            }
        )


class SymbolNotFoundError(ExchangeError):
    """Символ не найден на бирже"""

    def __init__(
        self,
        exchange_name: str,
        symbol: str,
        available_symbols: list | None = None,
        **kwargs,
    ):
        message = f"Symbol '{symbol}' not found on {exchange_name}"
        if available_symbols:
            message += f". Available symbols: {len(available_symbols)} total"

        super().__init__(message, exchange_name, **kwargs)

        self.context.update(
            {
                "symbol": symbol,
                "available_symbols_count": len(available_symbols) if available_symbols else 0,
            }
        )


class ExchangeMaintenanceError(ExchangeError):
    """Биржа находится на техническом обслуживании"""

    def __init__(
        self,
        exchange_name: str,
        maintenance_type: str = "scheduled",
        estimated_end_time: datetime | None = None,
        **kwargs,
    ):
        message = f"{exchange_name} is under {maintenance_type} maintenance"
        if estimated_end_time:
            message += f", estimated end: {estimated_end_time.isoformat()}"

        super().__init__(message, exchange_name, severity=ErrorSeverity.HIGH, **kwargs)

        self.context.update(
            {
                "maintenance_type": maintenance_type,
                "estimated_end_time": (
                    estimated_end_time.isoformat() if estimated_end_time else None
                ),
            }
        )


# =================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===================


def create_api_error_from_response(
    exchange_name: str,
    api_method: str,
    response_data: dict[str, Any],
    status_code: int | None = None,
) -> APIError:
    """Создание APIError из ответа биржи"""

    # Извлекаем код ошибки и сообщение в зависимости от формата биржи
    error_code = None
    api_message = None

    # Bybit format
    if "retCode" in response_data:
        error_code = str(response_data.get("retCode"))
        api_message = response_data.get("retMsg", "")

    # Binance format
    elif "code" in response_data:
        error_code = str(response_data.get("code"))
        api_message = response_data.get("msg", "")

    # Generic format
    elif "error" in response_data:
        error_data = response_data["error"]
        if isinstance(error_data, dict):
            error_code = str(error_data.get("code", ""))
            api_message = error_data.get("message", "")
        else:
            api_message = str(error_data)

    return APIError(
        exchange_name=exchange_name,
        api_method=api_method,
        error_code=error_code,
        api_message=api_message,
        status_code=status_code,
        response_data=response_data,
    )


def is_rate_limit_error(error_code: str, exchange_name: str) -> bool:
    """Проверка, является ли ошибка превышением rate limit"""

    rate_limit_codes = {
        "bybit": ["10006", "10018", "10019"],  # Rate limit codes for Bybit
        "binance": ["-1003", "-1015", "-2010"],  # Rate limit codes for Binance
        "okx": ["50011", "50014"],  # Rate limit codes for OKX
    }

    return error_code in rate_limit_codes.get(exchange_name.lower(), [])


def is_maintenance_error(error_code: str, exchange_name: str) -> bool:
    """Проверка, является ли ошибка техническим обслуживанием"""

    maintenance_codes = {
        "bybit": ["130021", "130048"],  # Maintenance codes for Bybit
        "binance": ["-1001", "-1021"],  # Maintenance codes for Binance
    }

    return error_code in maintenance_codes.get(exchange_name.lower(), [])


def extract_retry_after(
    response_data: dict[str, Any], headers: dict[str, str] | None = None
) -> int | None:
    """Извлечение времени retry из ответа биржи"""

    # Проверяем заголовки HTTP
    if headers:
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass

        # X-MBX-USED-WEIGHT для Binance
        if "X-MBX-USED-WEIGHT" in headers:
            try:
                used_weight = int(headers["X-MBX-USED-WEIGHT"])
                # Простая эвристика: если использовано >80% лимита, ждем 60 секунд
                if used_weight > 1000:  # Примерный лимит 1200
                    return 60
            except ValueError:
                pass

    # Проверяем тело ответа
    if "retry_after" in response_data:
        return response_data["retry_after"]

    # Стандартное время ожидания для rate limit
    return 60


def map_exchange_error_code(error_code: str, exchange_name: str) -> type[ExchangeError]:
    """Маппинг кода ошибки биржи к типу исключения"""

    # Общие коды ошибок
    if is_rate_limit_error(error_code, exchange_name):
        return RateLimitError

    if is_maintenance_error(error_code, exchange_name):
        return ExchangeMaintenanceError

    # Специфические коды для разных бирж
    if exchange_name.lower() == "bybit":
        bybit_error_map = {
            "10003": AuthenticationError,  # Invalid API key
            "10004": AuthenticationError,  # Invalid signature
            "20001": OrderRejectedError,  # Order rejected
            "20003": InsufficientBalanceError,  # Insufficient balance
            "110007": PositionNotFoundError,  # Position not found
            "130025": SymbolNotFoundError,  # Symbol not found
        }
        return bybit_error_map.get(error_code, APIError)

    elif exchange_name.lower() == "binance":
        binance_error_map = {
            "-2010": AuthenticationError,  # Invalid API key
            "-1022": AuthenticationError,  # Invalid signature
            "-2013": OrderNotFoundError,  # Order not found
            "-2019": InsufficientBalanceError,  # Insufficient balance
            "-1121": SymbolNotFoundError,  # Invalid symbol
        }
        return bybit_error_map.get(error_code, APIError)

    return APIError


# Константы для стандартных ошибок
COMMON_ERROR_MESSAGES = {
    "connection_timeout": "Connection to exchange timed out",
    "connection_refused": "Connection to exchange refused",
    "invalid_response": "Invalid response from exchange",
    "json_decode_error": "Failed to decode JSON response",
    "websocket_disconnected": "WebSocket connection lost",
    "symbol_not_supported": "Symbol not supported by exchange",
    "insufficient_balance": "Insufficient balance for operation",
    "order_size_too_small": "Order size below minimum",
    "order_size_too_large": "Order size above maximum",
    "invalid_price": "Invalid price value",
    "market_closed": "Market is closed",
    "position_not_open": "No open position found",
}
