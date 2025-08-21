"""
Data Adapters для BOT_Trading v3.0

Адаптеры для преобразования внутренних типов системы в модели веб-API.
Обеспечивают совместимость между core компонентами и web endpoints.

Преобразования:
- core.traders.Trader → TraderResponse
- exchanges.Position → PositionResponse
- exchanges.Order → OrderResponse
- monitoring.Metrics → MetricsResponse
- core.config → ConfigResponse
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union

from core.logging.logger_factory import get_global_logger_factory

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("data_adapters")


class DataAdapters:
    """
    Адаптеры данных для преобразования между внутренними типами и API моделями

    Основные возможности:
    - Преобразование моделей трейдеров
    - Преобразование торговых данных
    - Преобразование метрик и статистики
    - Обработка типов данных (Decimal → float, datetime → ISO string)
    - Валидация и очистка данных
    """

    def __init__(self):
        logger.info("DataAdapters инициализированы")

    # =================== TRADER ADAPTERS ===================

    def trader_to_response(self, trader) -> dict[str, Any]:
        """
        Преобразование внутреннего объекта трейдера в API response

        Args:
            trader: Объект трейдера из core.traders

        Returns:
            Словарь для TraderResponse
        """
        try:
            if trader is None:
                return {}

            # Получаем конфигурацию трейдера
            trader_config = trader.get_config("trader", {}) if hasattr(trader, "get_config") else {}

            # Базовая информация о трейдере
            response = {
                "trader_id": getattr(trader, "trader_id", "unknown"),
                "exchange": trader_config.get("exchange", "unknown"),
                "strategy": trader_config.get("strategy", "unknown"),
                "symbol": trader_config.get("symbol", "unknown"),
                "state": trader._state.value if hasattr(trader, "_state") else "unknown",
                "is_trading": getattr(trader, "_is_running", False),
                "created_at": self._datetime_to_iso(getattr(trader, "_created_at", None)),
                "last_activity": self._datetime_to_iso(
                    getattr(trader, "_started_at", None) or getattr(trader, "_created_at", None)
                ),
            }

            # Метрики производительности
            try:
                if hasattr(trader, "metrics"):
                    metrics = trader.metrics
                    response["performance"] = {
                        "total_trades": metrics.trades_total,
                        "winning_trades": metrics.trades_successful,
                        "losing_trades": metrics.trades_failed,
                        "win_rate": metrics.win_rate,
                        "profit_loss": metrics.profit_loss,
                        "max_drawdown": metrics.max_drawdown,
                        "current_positions": metrics.current_positions,
                        "last_trade_time": self._datetime_to_iso(metrics.last_trade_time),
                        "errors_count": metrics.errors_count,
                    }
                else:
                    response["performance"] = {}
            except Exception as e:
                logger.warning(f"Не удалось получить метрики производительности трейдера: {e}")
                response["performance"] = {}

            # Текущие позиции
            try:
                if hasattr(trader, "_positions"):
                    positions = list(trader._positions.values())
                    response["current_positions"] = (
                        self.positions_list_to_response(positions) if positions else []
                    )
                else:
                    response["current_positions"] = []
            except Exception as e:
                logger.warning(f"Не удалось получить текущие позиции трейдера: {e}")
                response["current_positions"] = []

            return response

        except Exception as e:
            logger.error(f"Ошибка преобразования трейдера в response: {e}")
            return {"error": f"Failed to convert trader: {e!s}"}

    def traders_list_to_response(self, traders: list) -> list[dict[str, Any]]:
        """Преобразование списка трейдеров"""
        return [self.trader_to_response(trader) for trader in traders if trader is not None]

    # =================== POSITION ADAPTERS ===================

    def position_to_response(self, position) -> dict[str, Any]:
        """
        Преобразование позиции в API response

        Args:
            position: Объект позиции из exchanges

        Returns:
            Словарь для PositionResponse
        """
        try:
            if position is None:
                return {}

            return {
                "symbol": getattr(position, "symbol", "unknown"),
                "side": getattr(position, "side", "unknown"),
                "size": self._decimal_to_float(getattr(position, "size", 0)),
                "entry_price": self._decimal_to_float(getattr(position, "entry_price", 0)),
                "mark_price": self._decimal_to_float(getattr(position, "mark_price", 0)),
                "unrealized_pnl": self._decimal_to_float(getattr(position, "unrealized_pnl", 0)),
                "realized_pnl": self._decimal_to_float(getattr(position, "realized_pnl", 0)),
                "margin": self._decimal_to_float(getattr(position, "margin", 0)),
                "leverage": self._decimal_to_float(getattr(position, "leverage", 1)),
                "created_at": self._datetime_to_iso(getattr(position, "created_at", None)),
                "updated_at": self._datetime_to_iso(getattr(position, "updated_at", None)),
            }

        except Exception as e:
            logger.error(f"Ошибка преобразования позиции в response: {e}")
            return {"error": f"Failed to convert position: {e!s}"}

    def positions_list_to_response(self, positions: list) -> list[dict[str, Any]]:
        """Преобразование списка позиций"""
        return [
            self.position_to_response(position) for position in positions if position is not None
        ]

    # =================== ORDER ADAPTERS ===================

    def order_to_response(self, order) -> dict[str, Any]:
        """
        Преобразование ордера в API response

        Args:
            order: Объект ордера из exchanges

        Returns:
            Словарь для OrderResponse
        """
        try:
            if order is None:
                return {}

            return {
                "order_id": getattr(order, "order_id", "unknown"),
                "client_order_id": getattr(order, "client_order_id", None),
                "symbol": getattr(order, "symbol", "unknown"),
                "side": getattr(order, "side", "unknown"),
                "order_type": getattr(order, "order_type", "unknown"),
                "quantity": self._decimal_to_float(getattr(order, "quantity", 0)),
                "price": self._decimal_to_float(getattr(order, "price", 0)),
                "filled_quantity": self._decimal_to_float(getattr(order, "filled_quantity", 0)),
                "remaining_quantity": self._decimal_to_float(
                    getattr(order, "remaining_quantity", 0)
                ),
                "average_price": self._decimal_to_float(getattr(order, "average_price", 0)),
                "status": getattr(order, "status", "unknown"),
                "time_in_force": getattr(order, "time_in_force", None),
                "created_at": self._datetime_to_iso(getattr(order, "created_at", None)),
                "updated_at": self._datetime_to_iso(getattr(order, "updated_at", None)),
                "filled_at": self._datetime_to_iso(getattr(order, "filled_at", None)),
            }

        except Exception as e:
            logger.error(f"Ошибка преобразования ордера в response: {e}")
            return {"error": f"Failed to convert order: {e!s}"}

    def orders_list_to_response(self, orders: list) -> list[dict[str, Any]]:
        """Преобразование списка ордеров"""
        return [self.order_to_response(order) for order in orders if order is not None]

    # =================== EXCHANGE ADAPTERS ===================

    def exchange_to_response(self, exchange) -> dict[str, Any]:
        """
        Преобразование объекта биржи в API response

        Args:
            exchange: Объект биржи из exchanges

        Returns:
            Словарь для ExchangeResponse
        """
        try:
            if exchange is None:
                return {}

            return {
                "name": getattr(exchange, "name", "unknown"),
                "display_name": getattr(
                    exchange, "display_name", getattr(exchange, "name", "unknown")
                ),
                "status": (
                    "connected"
                    if getattr(exchange, "is_connected", lambda: False)()
                    else "disconnected"
                ),
                "capabilities": self._capabilities_to_dict(getattr(exchange, "capabilities", None)),
                "api_limits": getattr(exchange, "api_limits", {}),
                "last_heartbeat": self._datetime_to_iso(getattr(exchange, "last_heartbeat", None)),
                "latency_ms": getattr(exchange, "latency_ms", None),
                "error_count": getattr(exchange, "error_count", 0),
                "success_rate": getattr(exchange, "success_rate", 100.0),
            }

        except Exception as e:
            logger.error(f"Ошибка преобразования биржи в response: {e}")
            return {"error": f"Failed to convert exchange: {e!s}"}

    def _capabilities_to_dict(self, capabilities) -> dict[str, bool]:
        """Преобразование capabilities в словарь"""
        if capabilities is None:
            return {}

        try:
            if hasattr(capabilities, "__dict__"):
                return {k: v for k, v in capabilities.__dict__.items() if isinstance(v, bool)}
            elif isinstance(capabilities, dict):
                return {k: v for k, v in capabilities.items() if isinstance(v, bool)}
            else:
                return {}
        except Exception as e:
            logger.warning(f"Не удалось преобразовать capabilities: {e}")
            return {}

    # =================== METRICS ADAPTERS ===================

    def metrics_to_response(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """
        Преобразование метрик в API response

        Args:
            metrics: Словарь с метриками из monitoring

        Returns:
            Очищенный словарь метрик
        """
        try:
            if not metrics:
                return {}

            cleaned_metrics = {}

            for key, value in metrics.items():
                if isinstance(value, (int, float)) or isinstance(value, Decimal):
                    cleaned_metrics[key] = float(value)
                elif isinstance(value, datetime):
                    cleaned_metrics[key] = value.isoformat()
                elif isinstance(value, (str, bool)):
                    cleaned_metrics[key] = value
                elif isinstance(value, dict):
                    cleaned_metrics[key] = self.metrics_to_response(value)
                elif isinstance(value, list):
                    cleaned_metrics[key] = [self._clean_metric_value(item) for item in value]
                else:
                    cleaned_metrics[key] = str(value)

            return cleaned_metrics

        except Exception as e:
            logger.error(f"Ошибка преобразования метрик в response: {e}")
            return {"error": f"Failed to convert metrics: {e!s}"}

    def _clean_performance_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Очистка метрик производительности"""
        if not metrics:
            return {}

        try:
            return {
                "total_pnl": self._decimal_to_float(metrics.get("total_pnl", 0.0)),
                "unrealized_pnl": self._decimal_to_float(metrics.get("unrealized_pnl", 0.0)),
                "realized_pnl": self._decimal_to_float(metrics.get("realized_pnl", 0.0)),
                "total_trades": int(metrics.get("total_trades", 0)),
                "winning_trades": int(metrics.get("winning_trades", 0)),
                "losing_trades": int(metrics.get("losing_trades", 0)),
                "win_rate": float(metrics.get("win_rate", 0.0)),
                "average_win": self._decimal_to_float(metrics.get("average_win", 0.0)),
                "average_loss": self._decimal_to_float(metrics.get("average_loss", 0.0)),
                "largest_win": self._decimal_to_float(metrics.get("largest_win", 0.0)),
                "largest_loss": self._decimal_to_float(metrics.get("largest_loss", 0.0)),
                "max_drawdown": self._decimal_to_float(metrics.get("max_drawdown", 0.0)),
                "sharpe_ratio": float(metrics.get("sharpe_ratio", 0.0)),
                "profit_factor": float(metrics.get("profit_factor", 0.0)),
                "last_updated": self._datetime_to_iso(metrics.get("last_updated")),
            }
        except Exception as e:
            logger.warning(f"Ошибка очистки метрик производительности: {e}")
            return {}

    # =================== STRATEGY ADAPTERS ===================

    def strategy_to_response(self, strategy) -> dict[str, Any]:
        """
        Преобразование стратегии в API response

        Args:
            strategy: Объект стратегии из strategies

        Returns:
            Словарь для StrategyResponse
        """
        try:
            if strategy is None:
                return {}

            return {
                "name": getattr(strategy, "name", "unknown"),
                "display_name": getattr(
                    strategy, "display_name", getattr(strategy, "name", "unknown")
                ),
                "description": getattr(strategy, "description", ""),
                "category": getattr(strategy, "category", "unknown"),
                "status": getattr(strategy, "status", "inactive"),
                "version": getattr(strategy, "version", "1.0.0"),
                "parameters": getattr(strategy, "default_parameters", {}),
                "supported_exchanges": getattr(strategy, "supported_exchanges", []),
                "risk_level": getattr(strategy, "risk_level", "medium"),
                "performance_metrics": self._get_strategy_performance(strategy),
            }

        except Exception as e:
            logger.error(f"Ошибка преобразования стратегии в response: {e}")
            return {"error": f"Failed to convert strategy: {e!s}"}

    def _get_strategy_performance(self, strategy) -> Optional[dict[str, float]]:
        """Получение метрик производительности стратегии"""
        try:
            if hasattr(strategy, "get_performance_metrics"):
                metrics = strategy.get_performance_metrics()
                return self._clean_performance_metrics(metrics)
            return None
        except Exception as e:
            logger.warning(f"Не удалось получить метрики производительности стратегии: {e}")
            return None

    # =================== CONFIG ADAPTERS ===================

    def config_to_response(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Преобразование конфигурации в API response

        Args:
            config: Словарь конфигурации

        Returns:
            Очищенный словарь конфигурации
        """
        try:
            if not config:
                return {}

            # Удаляем чувствительные данные
            safe_config = self._remove_sensitive_data(config.copy())

            # Очищаем типы данных
            return self._clean_config_values(safe_config)

        except Exception as e:
            logger.error(f"Ошибка преобразования конфигурации в response: {e}")
            return {"error": f"Failed to convert config: {e!s}"}

    def _remove_sensitive_data(self, config: dict[str, Any]) -> dict[str, Any]:
        """Удаление чувствительных данных из конфигурации"""
        sensitive_keys = {
            "api_key",
            "api_secret",
            "secret_key",
            "password",
            "token",
            "private_key",
            "access_token",
            "refresh_token",
            "webhook_secret",
        }

        def clean_dict(d):
            if isinstance(d, dict):
                return {
                    k: (
                        "***HIDDEN***"
                        if any(sens in k.lower() for sens in sensitive_keys)
                        else clean_dict(v)
                    )
                    for k, v in d.items()
                }
            elif isinstance(d, list):
                return [clean_dict(item) for item in d]
            else:
                return d

        return clean_dict(config)

    def _clean_config_values(self, config: dict[str, Any]) -> dict[str, Any]:
        """Очистка значений конфигурации"""

        def clean_value(value):
            if isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, dict):
                return {k: clean_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [clean_value(item) for item in value]
            else:
                return value

        return {k: clean_value(v) for k, v in config.items()}

    # =================== UTILITY METHODS ===================

    def _decimal_to_float(self, value: Union[Decimal, float, int, str, None]) -> float:
        """Преобразование Decimal в float"""
        if value is None:
            return 0.0

        try:
            if (
                isinstance(value, Decimal)
                or isinstance(value, (int, float))
                or isinstance(value, str)
            ):
                return float(value)
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _datetime_to_iso(self, dt: Optional[datetime]) -> Optional[str]:
        """Преобразование datetime в ISO строку"""
        if dt is None:
            return None

        try:
            if isinstance(dt, datetime):
                return dt.isoformat()
            elif isinstance(dt, str):
                return dt  # Уже строка
            else:
                return None
        except Exception:
            return None

    def _clean_metric_value(self, value: Any) -> Any:
        """Очистка значения метрики"""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, dict):
            return self.metrics_to_response(value)
        else:
            return value

    # =================== BATCH OPERATIONS ===================

    def batch_convert(self, items: list, converter_method: str) -> list[dict[str, Any]]:
        """
        Пакетное преобразование списка объектов

        Args:
            items: Список объектов для преобразования
            converter_method: Название метода для преобразования

        Returns:
            Список преобразованных объектов
        """
        if not items:
            return []

        try:
            converter = getattr(self, converter_method)
            return [converter(item) for item in items if item is not None]
        except AttributeError:
            logger.error(f"Метод конвертера {converter_method} не найден")
            return []
        except Exception as e:
            logger.error(f"Ошибка пакетного преобразования: {e}")
            return []

    # =================== VALIDATION ===================

    def validate_response_data(self, data: dict[str, Any]) -> bool:
        """Валидация данных response"""
        try:
            # Проверяем что нет None значений в обязательных полях
            if "error" in data:
                return True  # Ошибки валидны

            # Проверяем базовые типы данных
            for key, value in data.items():
                if value is None:
                    continue

                # Проверяем что числовые значения валидны
                if isinstance(value, (int, float)) and (value != value):  # NaN check
                    logger.warning(f"Найдено NaN значение в поле {key}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Ошибка валидации данных response: {e}")
            return False
