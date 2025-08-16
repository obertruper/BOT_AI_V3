"""
Configuration Validation для BOT_Trading v3.0

Система валидации конфигураций с поддержкой:
- Schema validation для всех типов конфигураций
- Проверка совместимости между компонентами
- Валидация API ключей и соединений
- Проверка бизнес-логики настроек
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationLevel(Enum):
    """Уровни валидации"""

    ERROR = "error"  # Критические ошибки
    WARNING = "warning"  # Предупреждения
    INFO = "info"  # Информационные сообщения


@dataclass
class ValidationResult:
    """Результат валидации"""

    level: ValidationLevel
    field: str
    message: str
    suggestion: str | None = None


class ConfigValidator:
    """
    Валидатор конфигураций для BOT_Trading v3.0

    Проверяет:
    - Структуру и типы данных
    - Бизнес-логику настроек
    - Совместимость компонентов
    - Безопасность конфигурации
    """

    def __init__(self):
        # Поддерживаемые биржи
        self.supported_exchanges = {
            "bybit",
            "binance",
            "okx",
            "bitget",
            "gateio",
            "kucoin",
            "huobi",
        }

        # Поддерживаемые стратегии
        self.supported_strategies = {
            "ml_strategy",
            "indicator_strategy",
            "arbitrage_strategy",
            "scalping_strategy",
            "grid_strategy",
        }

        # Допустимые типы рынков
        self.supported_market_types = {"spot", "futures", "margin"}

        # Минимальные требования
        self.min_leverage = 1.0
        self.max_leverage = 100.0
        self.min_balance = 10.0
        self.max_position_size = 10000.0

    def validate_system_config(self, config: dict[str, Any]) -> list[ValidationResult]:
        """Валидация системной конфигурации"""
        results = []

        # Проверка обязательных полей
        required_fields = ["name", "version"]
        for field in required_fields:
            if field not in config:
                results.append(
                    ValidationResult(
                        ValidationLevel.ERROR,
                        f"system.{field}",
                        f"Отсутствует обязательное поле '{field}'",
                        f"Добавьте поле '{field}' в конфигурацию",
                    )
                )

        # Проверка лимитов системы
        limits = config.get("limits", {})
        if limits:
            results.extend(self._validate_system_limits(limits))

        # Проверка настроек производительности
        performance = config.get("performance", {})
        if performance:
            results.extend(self._validate_performance_config(performance))

        return results

    def validate_database_config(self, config: dict[str, Any]) -> list[ValidationResult]:
        """Валидация конфигурации базы данных"""
        results = []

        # Проверка обязательных полей
        required_fields = ["host", "port", "name", "user"]
        for field in required_fields:
            if field not in config:
                results.append(
                    ValidationResult(
                        ValidationLevel.ERROR,
                        f"database.{field}",
                        f"Отсутствует обязательное поле '{field}'",
                        f"Добавьте поле '{field}' в конфигурацию базы данных",
                    )
                )

        # Проверка типа БД
        db_type = config.get("type", "postgresql")
        if db_type != "postgresql":
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    "database.type",
                    f"Рекомендуется использовать PostgreSQL, указан: {db_type}",
                    "Измените тип на 'postgresql' для оптимальной производительности",
                )
            )

        # Проверка порта
        port = config.get("port")
        if port and not (1 <= int(port) <= 65535):
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    "database.port",
                    f"Некорректный порт: {port}",
                    "Укажите порт в диапазоне 1-65535",
                )
            )

        # Проверка настроек пула соединений
        pool = config.get("pool", {})
        if pool:
            results.extend(self._validate_connection_pool(pool))

        return results

    def validate_trader_config(
        self, trader_id: str, config: dict[str, Any]
    ) -> list[ValidationResult]:
        """Валидация конфигурации трейдера"""
        results = []

        # Проверка обязательных полей
        required_fields = ["exchange", "strategy"]
        for field in required_fields:
            if field not in config:
                results.append(
                    ValidationResult(
                        ValidationLevel.ERROR,
                        f"trader.{trader_id}.{field}",
                        f"Отсутствует обязательное поле '{field}'",
                        f"Добавьте поле '{field}' в конфигурацию трейдера",
                    )
                )

        # Проверка биржи
        exchange = config.get("exchange")
        if exchange and exchange not in self.supported_exchanges:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    f"trader.{trader_id}.exchange",
                    f"Неподдерживаемая биржа: {exchange}",
                    f"Используйте одну из поддерживаемых: {', '.join(self.supported_exchanges)}",
                )
            )

        # Проверка стратегии
        strategy = config.get("strategy")
        if strategy and strategy not in self.supported_strategies:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    f"trader.{trader_id}.strategy",
                    f"Возможно неподдерживаемая стратегия: {strategy}",
                    f"Рекомендуемые стратегии: {', '.join(self.supported_strategies)}",
                )
            )

        # Проверка типа рынка
        market_type = config.get("market_type", "futures")
        if market_type not in self.supported_market_types:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    f"trader.{trader_id}.market_type",
                    f"Неподдерживаемый тип рынка: {market_type}",
                    f"Используйте: {', '.join(self.supported_market_types)}",
                )
            )

        # Проверка конфигурации биржи
        exchange_config = config.get("exchange_config", {})
        if exchange_config:
            results.extend(self._validate_exchange_config(trader_id, exchange_config))

        # Проверка управления рисками
        risk_management = config.get("risk_management", {})
        if risk_management:
            results.extend(self._validate_risk_management(trader_id, risk_management))

        return results

    def validate_exchange_config(
        self, exchange: str, config: dict[str, Any]
    ) -> list[ValidationResult]:
        """Валидация конфигурации биржи"""
        results = []

        # Проверка API ключей
        api_key = config.get("api_key")
        if not api_key:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    f"exchange.{exchange}.api_key",
                    "Отсутствует API ключ",
                    "Добавьте API ключ для доступа к бирже",
                )
            )
        elif not self._is_valid_api_key_format(api_key):
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    f"exchange.{exchange}.api_key",
                    "Возможно некорректный формат API ключа",
                    "Проверьте правильность API ключа",
                )
            )

        api_secret = config.get("api_secret")
        if not api_secret:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    f"exchange.{exchange}.api_secret",
                    "Отсутствует API секрет",
                    "Добавьте API секрет для доступа к бирже",
                )
            )

        # Проверка testnet режима
        testnet = config.get("testnet", False)
        if not testnet:
            results.append(
                ValidationResult(
                    ValidationLevel.INFO,
                    f"exchange.{exchange}.testnet",
                    "Используется production режим",
                    "Убедитесь, что это production окружение",
                )
            )

        return results

    def _validate_system_limits(self, limits: dict[str, Any]) -> list[ValidationResult]:
        """Валидация системных лимитов"""
        results = []

        # Проверка максимального количества трейдеров
        max_traders = limits.get("max_traders", 0)
        if max_traders <= 0:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    "system.limits.max_traders",
                    "Не установлен лимит на количество трейдеров",
                    "Рекомендуется установить разумный лимит (например, 10)",
                )
            )
        elif max_traders > 50:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    "system.limits.max_traders",
                    f"Очень большой лимит трейдеров: {max_traders}",
                    "Рекомендуется не более 20 трейдеров для стабильности",
                )
            )

        # Проверка лимитов памяти
        max_memory = limits.get("max_memory_usage_mb", 0)
        if max_memory > 0 and max_memory < 512:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    "system.limits.max_memory_usage_mb",
                    f"Низкий лимит памяти: {max_memory}MB",
                    "Рекомендуется минимум 1024MB для стабильной работы",
                )
            )

        return results

    def _validate_performance_config(self, performance: dict[str, Any]) -> list[ValidationResult]:
        """Валидация настроек производительности"""
        results = []

        # Проверка количества потоков
        worker_threads = performance.get("worker_threads", 1)
        if worker_threads <= 0:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    "system.performance.worker_threads",
                    "Количество рабочих потоков должно быть больше 0",
                    "Установите значение от 2 до 8",
                )
            )
        elif worker_threads > 16:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    "system.performance.worker_threads",
                    f"Большое количество потоков: {worker_threads}",
                    "Обычно достаточно 4-8 потоков",
                )
            )

        return results

    def _validate_connection_pool(self, pool: dict[str, Any]) -> list[ValidationResult]:
        """Валидация настроек пула соединений"""
        results = []

        min_conn = pool.get("min_connections", 0)
        max_conn = pool.get("max_connections", 0)

        if min_conn <= 0:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    "database.pool.min_connections",
                    "Минимальное количество соединений должно быть больше 0",
                    "Рекомендуется значение 2-5",
                )
            )

        if max_conn <= min_conn:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    "database.pool.max_connections",
                    "Максимальное количество соединений должно быть больше минимального",
                    f"Установите значение больше {min_conn}",
                )
            )

        return results

    def _validate_exchange_config(
        self, trader_id: str, config: dict[str, Any]
    ) -> list[ValidationResult]:
        """Валидация конфигурации биржи для трейдера"""
        results = []

        # Проверка наличия credentials
        required_fields = ["api_key", "api_secret"]
        for field in required_fields:
            if not config.get(field):
                results.append(
                    ValidationResult(
                        ValidationLevel.ERROR,
                        f"trader.{trader_id}.exchange_config.{field}",
                        f"Отсутствует {field}",
                        f"Добавьте {field} для подключения к бирже",
                    )
                )

        return results

    def _validate_risk_management(
        self, trader_id: str, config: dict[str, Any]
    ) -> list[ValidationResult]:
        """Валидация настроек управления рисками"""
        results = []

        # Проверка leverage
        leverage = config.get("leverage", 1.0)
        if leverage < self.min_leverage or leverage > self.max_leverage:
            results.append(
                ValidationResult(
                    ValidationLevel.ERROR,
                    f"trader.{trader_id}.risk_management.leverage",
                    f"Leverage {leverage} вне допустимого диапазона",
                    f"Используйте значение от {self.min_leverage} до {self.max_leverage}",
                )
            )

        # Проверка размера позиции
        max_position = config.get("max_position_size")
        if max_position and max_position > self.max_position_size:
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    f"trader.{trader_id}.risk_management.max_position_size",
                    f"Большой размер позиции: {max_position}",
                    f"Рекомендуется не более {self.max_position_size}",
                )
            )

        # Проверка stop loss
        stop_loss = config.get("stop_loss_percent")
        if stop_loss and (stop_loss <= 0 or stop_loss > 50):
            results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    f"trader.{trader_id}.risk_management.stop_loss_percent",
                    f"Нестандартный stop loss: {stop_loss}%",
                    "Рекомендуется значение от 1% до 10%",
                )
            )

        return results

    def _is_valid_api_key_format(self, api_key: str) -> bool:
        """Проверка формата API ключа"""
        # Базовые проверки формата API ключа
        if len(api_key) < 10:
            return False

        # Проверка на placeholder значения
        placeholder_patterns = [
            "your_api_key",
            "api_key_here",
            "replace_with_key",
            "test_key",
            "demo_key",
            "example_key",
        ]

        return not any(pattern in api_key.lower() for pattern in placeholder_patterns)

    def validate_all(self, config: dict[str, Any]) -> list[ValidationResult]:
        """Полная валидация всей конфигурации"""
        results = []

        # Валидация системной конфигурации
        system_config = config.get("system", {})
        if system_config:
            results.extend(self.validate_system_config(system_config))

        # Валидация БД
        database_config = config.get("database") or config.get("postgres", {})
        if database_config:
            results.extend(self.validate_database_config(database_config))

        # Валидация трейдеров
        traders = config.get("traders", [])
        for trader in traders:
            trader_id = trader.get("id", "unknown")
            results.extend(self.validate_trader_config(trader_id, trader))

        return results

    def get_validation_summary(self, results: list[ValidationResult]) -> dict[str, int]:
        """Получение сводки по результатам валидации"""
        summary = {
            "errors": len([r for r in results if r.level == ValidationLevel.ERROR]),
            "warnings": len([r for r in results if r.level == ValidationLevel.WARNING]),
            "info": len([r for r in results if r.level == ValidationLevel.INFO]),
            "total": len(results),
        }
        return summary
